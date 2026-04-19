import argparse
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Iterable


DB_PATH = Path("clan_book.db")


class ClanBook:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                clan_name TEXT,
                gender TEXT,
                birth_year INTEGER,
                notes TEXT,
                father_name_text TEXT,
                mother_name_text TEXT,
                father_id INTEGER,
                mother_id INTEGER,
                FOREIGN KEY (father_id) REFERENCES people (id),
                FOREIGN KEY (mother_id) REFERENCES people (id)
            )
            """
        )
        self._ensure_column("father_name_text", "TEXT")
        self._ensure_column("mother_name_text", "TEXT")
        self.connection.commit()

    def _ensure_column(self, column_name: str, column_type: str) -> None:
        columns = self.connection.execute("PRAGMA table_info(people)").fetchall()
        column_names = {column["name"] for column in columns}
        if column_name in column_names:
            return
        self.connection.execute(
            f"ALTER TABLE people ADD COLUMN {column_name} {column_type}"
        )

    def close(self) -> None:
        self.connection.close()

    def _get_person_by_name(self, full_name: str) -> sqlite3.Row | None:
        cursor = self.connection.execute(
            "SELECT * FROM people WHERE full_name = ?",
            (full_name.strip(),),
        )
        return cursor.fetchone()

    def _get_person_by_id(self, person_id: int) -> sqlite3.Row | None:
        cursor = self.connection.execute(
            "SELECT * FROM people WHERE id = ?",
            (person_id,),
        )
        return cursor.fetchone()

    def _find_person_id(self, full_name: str | None) -> int | None:
        if not full_name:
            return None

        person = self._get_person_by_name(full_name)
        if person is None:
            return None
        return int(person["id"])

    def add_person(
        self,
        full_name: str,
        clan_name: str | None = None,
        gender: str | None = None,
        notes: str | None = None,
        father_name: str | None = None,
        mother_name: str | None = None,
    ) -> None:
        cleaned_name = full_name.strip()
        if not cleaned_name:
            raise ValueError("Ingiza majina yako mawili.")

        father_name_clean = father_name.strip() if father_name else None
        mother_name_clean = mother_name.strip() if mother_name else None
        father_id = self._find_person_id(father_name_clean)
        mother_id = self._find_person_id(mother_name_clean)

        self.connection.execute(
            """
            INSERT INTO people (
                full_name,
                clan_name,
                gender,
                birth_year,
                notes,
                father_name_text,
                mother_name_text,
                father_id,
                mother_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned_name,
                clan_name.strip() if clan_name else None,
                gender.strip() if gender else None,
                None,
                notes.strip() if notes else None,
                father_name_clean,
                mother_name_clean,
                father_id,
                mother_id,
            ),
        )
        self._link_family_connections(cleaned_name)
        self.connection.commit()

    def list_people(self) -> Iterable[sqlite3.Row]:
        cursor = self.connection.execute(
            "SELECT * FROM people ORDER BY full_name COLLATE NOCASE"
        )
        return cursor.fetchall()

    def get_person_details(self, full_name: str) -> sqlite3.Row | None:
        cursor = self.connection.execute(
            """
            SELECT
                child.*,
                COALESCE(father.full_name, child.father_name_text) AS father_name,
                COALESCE(mother.full_name, child.mother_name_text) AS mother_name
            FROM people AS child
            LEFT JOIN people AS father ON father.id = child.father_id
            LEFT JOIN people AS mother ON mother.id = child.mother_id
            WHERE child.full_name = ?
            """,
            (full_name.strip(),),
        )
        return cursor.fetchone()

    def _link_family_connections(self, full_name: str) -> None:
        person = self._get_person_by_name(full_name)
        if not person:
            return

        person_id = int(person["id"])
        father_name_text = person["father_name_text"]
        mother_name_text = person["mother_name_text"]

        if father_name_text and not person["father_id"]:
            father_id = self._find_person_id(father_name_text)
            if father_id:
                self.connection.execute(
                    "UPDATE people SET father_id = ? WHERE id = ?",
                    (father_id, person_id),
                )

        if mother_name_text and not person["mother_id"]:
            mother_id = self._find_person_id(mother_name_text)
            if mother_id:
                self.connection.execute(
                    "UPDATE people SET mother_id = ? WHERE id = ?",
                    (mother_id, person_id),
                )

        self.connection.execute(
            """
            UPDATE people
            SET father_id = (
                SELECT id FROM people AS parent
                WHERE parent.full_name = people.father_name_text
            )
            WHERE father_name_text = ?
              AND (father_id IS NULL OR father_id != ?)
            """,
            (full_name, person_id),
        )

        self.connection.execute(
            """
            UPDATE people
            SET mother_id = (
                SELECT id FROM people AS parent
                WHERE parent.full_name = people.mother_name_text
            )
            WHERE mother_name_text = ?
              AND (mother_id IS NULL OR mother_id != ?)
            """,
            (full_name, person_id),
        )

    def lineage(self, full_name: str) -> list[str]:
        person = self.get_person_details(full_name)
        if person is None:
            raise ValueError(f"'{full_name}' was not found in the clan book.")

        lines = [f"{person['full_name']}"]
        self._append_parent_line(lines, person["father_name"], "Father", 1)
        self._append_parent_line(lines, person["mother_name"], "Mother", 1)
        return lines

    def _append_parent_line(
        self, lines: list[str], parent_name: str | None, label: str, level: int
    ) -> None:
        indent = "  " * level
        if not parent_name:
            lines.append(f"{indent}{label}: Unknown")
            return

        lines.append(f"{indent}{label}: {parent_name}")
        parent = self.get_person_details(parent_name)
        if not parent:
            return

        self._append_parent_line(lines, parent["father_name"], "Father", level + 1)
        self._append_parent_line(lines, parent["mother_name"], "Mother", level + 1)

    def _parent_ids(self, person: sqlite3.Row) -> set[int]:
        parent_ids: set[int] = set()
        if person["father_id"]:
            parent_ids.add(int(person["father_id"]))
        if person["mother_id"]:
            parent_ids.add(int(person["mother_id"]))
        return parent_ids

    def _children_of(self, person_id: int) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            """
            SELECT * FROM people
            WHERE father_id = ? OR mother_id = ?
            ORDER BY full_name COLLATE NOCASE
            """,
            (person_id, person_id),
        )
        return cursor.fetchall()

    def describe_relationship(self, base_name: str, target_name: str) -> str:
        base = self.get_person_details(base_name)
        target = self.get_person_details(target_name)

        if not base:
            raise ValueError(f"'{base_name}' hakupatikana kwenye daftari la ukoo.")
        if not target:
            raise ValueError(f"'{target_name}' hakupatikana kwenye daftari la ukoo.")

        if base["id"] == target["id"]:
            return f"{target_name} ni wewe mwenyewe."

        base_id = int(base["id"])
        target_id = int(target["id"])
        target_gender = (target["gender"] or "").strip().lower()
        base_parents = self._parent_ids(base)
        target_parents = self._parent_ids(target)

        if base["father_id"] and int(base["father_id"]) == target_id:
            return f"{target_name} ni baba yako."
        if base["mother_id"] and int(base["mother_id"]) == target_id:
            return f"{target_name} ni mama yako."
        if target_id in base_parents:
            return f"{target_name} ni mzazi wako."

        if target["father_id"] and int(target["father_id"]) == base_id:
            return f"{target_name} ni {'mwanao wa kiume' if target_gender == 'male' else 'mwanao wa kike' if target_gender == 'female' else 'mtoto wako'}."
        if target["mother_id"] and int(target["mother_id"]) == base_id:
            return f"{target_name} ni {'mwanao wa kiume' if target_gender == 'male' else 'mwanao wa kike' if target_gender == 'female' else 'mtoto wako'}."
        if base_id in target_parents:
            return f"{target_name} ni {'mwanao wa kiume' if target_gender == 'male' else 'mwanao wa kike' if target_gender == 'female' else 'mtoto wako'}."

        shared_parents = base_parents & target_parents
        if shared_parents:
            sibling_word = (
                "ndugu yako wa kiume" if target_gender == "male" else "ndugu yako wa kike" if target_gender == "female" else "ndugu yako"
            )
            return f"{target_name} ni {sibling_word}."

        grandparents = set()
        for parent_id in base_parents:
            parent = self._get_person_by_id(parent_id)
            if parent:
                grandparents |= self._parent_ids(parent)
        if target_id in grandparents:
            return f"{target_name} ni babu au bibi yako."

        grandchildren = set()
        for child in self._children_of(base_id):
            grandchildren |= {int(grandchild['id']) for grandchild in self._children_of(int(child["id"]))}
        if target_id in grandchildren:
            return f"{target_name} ni mjukuu wako."

        parent_siblings = set()
        for parent_id in base_parents:
            parent = self._get_person_by_id(parent_id)
            if parent:
                parent_siblings |= self._siblings_of(parent)
        if target_id in parent_siblings:
            return f"{target_name} ni shangazi, mjomba, ama ami yako."

        base_siblings = self._siblings_of(base)
        nieces_nephews = set()
        for sibling_id in base_siblings:
            for child in self._children_of(sibling_id):
                nieces_nephews.add(int(child["id"]))
        if target_id in nieces_nephews:
            return f"{target_name} ni mtoto wa ndugu yako."

        cousins = set()
        for parent_id in base_parents:
            parent = self._get_person_by_id(parent_id)
            if not parent:
                continue
            for aunt_uncle_id in self._siblings_of(parent):
                for cousin in self._children_of(aunt_uncle_id):
                    cousins.add(int(cousin["id"]))
        if target_id in cousins:
            return f"{target_name} ni binamu yako."

        return (
            f"{target_name} amesajiliwa, lakini programu bado haiwezi kutambua "
            "uhusiano wenu halisi kutokana na taarifa za familia zilizounganishwa."
        )

    def _siblings_of(self, person: sqlite3.Row) -> set[int]:
        person_id = int(person["id"])
        parent_ids = self._parent_ids(person)
        siblings: set[int] = set()
        if not parent_ids:
            return siblings

        for parent_id in parent_ids:
            for child in self._children_of(parent_id):
                child_id = int(child["id"])
                if child_id != person_id:
                    siblings.add(child_id)
        return siblings


class ClanBookApp:
    def __init__(self, root: tk.Tk, book: ClanBook) -> None:
        self.root = root
        self.book = book

        self.root.title("Usajili wa Ukoo")
        self.root.geometry("760x560")
        self.root.minsize(680, 520)

        self.current_user_name: str | None = None
        self.login_name_var = tk.StringVar()
        self.search_name_var = tk.StringVar()
        self.first_name_var = tk.StringVar()
        self.second_name_var = tk.StringVar()
        self.clan_name_var = tk.StringVar()
        self.gender_var = tk.StringVar()
        self.father_name_var = tk.StringVar()
        self.mother_name_var = tk.StringVar()

        self._configure_style()
        self._build_layout()

    def _configure_style(self) -> None:
        self.root.configure(bg="#f3efe4")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f3efe4")
        style.configure("Card.TFrame", background="#fffaf0", relief="flat")
        style.configure("Title.TLabel", background="#f3efe4", foreground="#2c2419")
        style.configure(
            "Heading.TLabel",
            background="#fffaf0",
            foreground="#513d1f",
            font=("Georgia", 15, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background="#fffaf0",
            foreground="#2c2419",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=8,
        )

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=18)
        outer.pack(fill="both", expand=True)

        self.header_title = ttk.Label(
            outer,
            text="Daftari la Ukoo",
            style="Title.TLabel",
            font=("Georgia", 24, "bold"),
        )
        self.header_title.pack(anchor="w")

        self.header_subtitle = ttk.Label(
            outer,
            text="Chagua kuingia kama tayari umesajiliwa, au jisajili kuunda taarifa mpya.",
            style="Title.TLabel",
            font=("Segoe UI", 11),
        )
        self.header_subtitle.pack(anchor="w", pady=(4, 14))

        self.content = ttk.Frame(outer, style="App.TFrame")
        self.content.pack(fill="both", expand=True)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.show_home_view()

    def _clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

    def show_home_view(self) -> None:
        self._clear_content()
        self.header_title.config(text="Daftari la Ukoo")
        self.header_subtitle.config(
            text="Chagua kuingia kama tayari umesajiliwa, au jisajili kuunda taarifa mpya."
        )

        card = ttk.Frame(self.content, style="Card.TFrame", padding=24)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Karibu", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        message = (
            "Huu ndio ukurasa wa kwanza wa programu ya ukoo.\n"
            "Chagua Ingia kama mtu tayari amesajiliwa,\n"
            "au chagua Jisajili kwa mtu mpya."
        )
        ttk.Label(
            card,
            text=message,
            style="Body.TLabel",
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 20))

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=2, column=0, sticky="ew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ttk.Button(
            buttons,
            text="Ingia",
            style="Accent.TButton",
            command=self.show_login_view,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Jisajili",
            command=self.show_register_view,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def show_login_view(self) -> None:
        self._clear_content()
        self.header_title.config(text="Ingia")
        self.header_subtitle.config(
            text="Weka jina kamili la mtu kuendelea kama tayari amesajiliwa."
        )

        card = ttk.Frame(self.content, style="Card.TFrame", padding=24)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Ingia", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )
        ttk.Label(card, text="Jina kamili", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=6
        )
        ttk.Entry(card, textvariable=self.login_name_var).grid(
            row=1, column=1, sticky="ew", pady=6
        )

        button_row = ttk.Frame(card, style="Card.TFrame")
        button_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)

        ttk.Button(
            button_row,
            text="Endelea",
            style="Accent.TButton",
            command=self.login_person,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Rudi",
            command=self.show_home_view,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def show_register_view(self) -> None:
        self._clear_content()
        self.header_title.config(text="Jisajili")
        self.header_subtitle.config(
            text="Weka taarifa za mtu ili asajiliwe kwenye daftari la ukoo."
        )
        self._build_form(self.content)

    def _build_form(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Fomu ya Usajili", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        fields = [
            ("Jina la kwanza", self.first_name_var),
            ("Jina la pili", self.second_name_var),
            ("Jina la ukoo", self.clan_name_var),
            ("Jinsia", self.gender_var),
            ("Jina kamili la baba", self.father_name_var),
            ("Jina kamili la mama", self.mother_name_var),
        ]

        for row_index, (label, variable) in enumerate(fields, start=1):
            ttk.Label(card, text=label, style="Body.TLabel").grid(
                row=row_index, column=0, sticky="w", padx=(0, 12), pady=6
            )
            ttk.Entry(card, textvariable=variable).grid(
                row=row_index, column=1, sticky="ew", pady=6
            )

        ttk.Label(card, text="Maelezo", style="Body.TLabel").grid(
            row=7, column=0, sticky="nw", padx=(0, 12), pady=6
        )
        self.notes_text = tk.Text(
            card,
            height=4,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#2c2419",
        )
        self.notes_text.grid(row=7, column=1, sticky="ew", pady=6)

        button_row = ttk.Frame(card, style="Card.TFrame")
        button_row.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        ttk.Button(
            button_row,
            text="Hifadhi",
            style="Accent.TButton",
            command=self.save_person,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Futa Fomu",
            command=self.clear_form,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 6))

        ttk.Button(
            button_row,
            text="Rudi",
            command=self.show_home_view,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

    def show_search_view(self) -> None:
        self._clear_content()
        self.header_title.config(text="Tafuta Uhusiano")
        self.header_subtitle.config(
            text="Tafuta mtu aliyesajiliwa uone ana uhusiano gani na wewe."
        )

        card = ttk.Frame(self.content, style="Card.TFrame", padding=24)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        current_name = self.current_user_name or ""
        ttk.Label(card, text="Umeingia kama", style="Body.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=6
        )
        ttk.Label(card, text=current_name, style="Heading.TLabel").grid(
            row=0, column=1, sticky="w", pady=6
        )

        ttk.Label(card, text="Tafuta mtu", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=6
        )
        ttk.Entry(card, textvariable=self.search_name_var).grid(
            row=1, column=1, sticky="ew", pady=6
        )

        button_row = ttk.Frame(card, style="Card.TFrame")
        button_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 10))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        ttk.Button(
            button_row,
            text="Tafuta",
            style="Accent.TButton",
            command=self.search_relationship,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Tafuta Tena",
            command=lambda: self.search_name_var.set(""),
        ).grid(row=0, column=1, sticky="ew", padx=6)

        ttk.Button(
            button_row,
            text="Toka",
            command=self.logout_person,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        ttk.Label(card, text="Majibu", style="Body.TLabel").grid(
            row=3, column=0, sticky="nw", padx=(0, 12), pady=6
        )
        self.search_result_text = tk.Text(
            card,
            height=8,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#2c2419",
        )
        self.search_result_text.grid(row=3, column=1, sticky="nsew", pady=6)
        self.search_result_text.insert(
            "1.0",
            "Weka jina kamili la mtu aliyesajiliwa, kisha bonyeza Tafuta.",
        )
        self.search_result_text.config(state="disabled")

    def login_person(self) -> None:
        full_name = self.login_name_var.get().strip()
        if not full_name:
            messagebox.showerror("Ingia", "Weka jina kamili kwanza.")
            return

        person = self.book.get_person_details(full_name)
        if not person:
            messagebox.showerror(
                "Hajapatikana",
                f"{full_name} bado hajasajiliwa. Tafadhali tumia Jisajili.",
            )
            return

        self.current_user_name = full_name
        self.login_name_var.set("")
        self.search_name_var.set("")
        self.show_search_view()

    def save_person(self) -> None:
        try:
            full_name = self.build_full_name()
            self.book.add_person(
                full_name=full_name,
                clan_name=self.clan_name_var.get() or None,
                gender=self.gender_var.get() or None,
                notes=self.notes_text.get("1.0", tk.END).strip() or None,
                father_name=self.father_name_var.get() or None,
                mother_name=self.mother_name_var.get() or None,
            )
        except ValueError as error:
            messagebox.showerror("Haiwezi kuhifadhi", str(error))
            return
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Haiwezi kuhifadhi",
                "Mtu huyo tayari yupo kwenye daftari la ukoo.",
            )
            return

        self.clear_form()
        messagebox.showinfo("Imehifadhiwa", f"{full_name} ameongezwa kwa mafanikio.")

    def build_full_name(self) -> str:
        first_name = self.first_name_var.get().strip()
        second_name = self.second_name_var.get().strip()
        full_name = " ".join(part for part in [first_name, second_name] if part)
        if not full_name:
            raise ValueError("Weka angalau jina moja.")
        return full_name

    def clear_form(self) -> None:
        self.first_name_var.set("")
        self.second_name_var.set("")
        self.clan_name_var.set("")
        self.gender_var.set("")
        self.father_name_var.set("")
        self.mother_name_var.set("")
        self.notes_text.delete("1.0", tk.END)

    def set_result_text(self, text: str) -> None:
        self.search_result_text.config(state="normal")
        self.search_result_text.delete("1.0", tk.END)
        self.search_result_text.insert("1.0", text)
        self.search_result_text.config(state="disabled")

    def search_relationship(self) -> None:
        if not self.current_user_name:
            messagebox.showerror("Tafuta", "Ingia kwanza.")
            return

        target_name = self.search_name_var.get().strip()
        if not target_name:
            messagebox.showerror("Tafuta", "Weka jina kamili la mtu unayetafuta.")
            return

        try:
            relationship = self.book.describe_relationship(
                self.current_user_name, target_name
            )
        except ValueError as error:
            messagebox.showerror("Tafuta", str(error))
            return

        self.set_result_text(relationship)

    def logout_person(self) -> None:
        self.current_user_name = None
        self.search_name_var.set("")
        self.show_home_view()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sajili watu wa ukoo na fuatilia uhusiano wa familia."
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Sajili mtu mpya.")
    add_parser.add_argument("--name", required=True, help="Jina kamili la mtu.")
    add_parser.add_argument("--clan", help="Jina la ukoo.")
    add_parser.add_argument("--gender", help="Jinsia.")
    add_parser.add_argument("--notes", help="Maelezo ya ziada.")
    add_parser.add_argument("--father", help="Jina kamili la baba.")
    add_parser.add_argument("--mother", help="Jina kamili la mama.")

    subparsers.add_parser("list", help="Orodhesha watu wote waliosajiliwa.")

    details_parser = subparsers.add_parser("details", help="Onyesha taarifa za mtu mmoja.")
    details_parser.add_argument("--name", required=True, help="Jina kamili la kutafuta.")

    lineage_parser = subparsers.add_parser(
        "lineage", help="Onyesha mlolongo wa wazazi wa mtu."
    )
    lineage_parser.add_argument("--name", required=True, help="Jina kamili la kutafuta.")

    return parser


def run_gui(book: ClanBook) -> None:
    root = tk.Tk()
    app = ClanBookApp(root, book)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, book))
    root.mainloop()


def on_close(root: tk.Tk, book: ClanBook) -> None:
    book.close()
    root.destroy()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    book = ClanBook()

    try:
        if not args.command:
            run_gui(book)
            return

        if args.command == "add":
            book.add_person(
                full_name=args.name,
                clan_name=args.clan,
                gender=args.gender,
                notes=args.notes,
                father_name=args.father,
                mother_name=args.mother,
            )
            print(f"{args.name} amesajiliwa.")
        elif args.command == "list":
            people = list(book.list_people())
            if not people:
                print("Bado hakuna watu waliosajiliwa.")
                return
            for person in people:
                print(person["full_name"])
        elif args.command == "details":
            details = book.get_person_details(args.name)
            if not details:
                raise ValueError(f"'{args.name}' hakupatikana kwenye daftari la ukoo.")
            print(f"Jina: {details['full_name']}")
            print(f"Ukoo: {details['clan_name'] or 'Haijawekwa'}")
            print(f"Jinsia: {details['gender'] or 'Haijawekwa'}")
            print(f"Baba: {details['father_name'] or 'Hajulikani'}")
            print(f"Mama: {details['mother_name'] or 'Hajulikani'}")
            print(f"Maelezo: {details['notes'] or 'Hakuna'}")
        elif args.command == "lineage":
            for line in book.lineage(args.name):
                print(line)
    finally:
        if args.command:
            book.close()


if __name__ == "__main__":
    main()
