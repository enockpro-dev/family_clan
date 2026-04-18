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
                father_id INTEGER,
                mother_id INTEGER,
                FOREIGN KEY (father_id) REFERENCES people (id),
                FOREIGN KEY (mother_id) REFERENCES people (id)
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _get_person_by_name(self, full_name: str) -> sqlite3.Row | None:
        cursor = self.connection.execute(
            "SELECT * FROM people WHERE full_name = ?",
            (full_name.strip(),),
        )
        return cursor.fetchone()

    def _require_person_id(self, full_name: str | None) -> int | None:
        if not full_name:
            return None

        person = self._get_person_by_name(full_name)
        if person is None:
            raise ValueError(
                f"'{full_name}' was not found. Add that parent first before linking them."
            )
        return int(person["id"])

    def add_person(
        self,
        full_name: str,
        clan_name: str | None = None,
        gender: str | None = None,
        birth_year: int | None = None,
        notes: str | None = None,
        father_name: str | None = None,
        mother_name: str | None = None,
    ) -> None:
        cleaned_name = full_name.strip()
        if not cleaned_name:
            raise ValueError("Full name is required.")

        father_id = self._require_person_id(father_name)
        mother_id = self._require_person_id(mother_name)

        self.connection.execute(
            """
            INSERT INTO people (
                full_name, clan_name, gender, birth_year, notes, father_id, mother_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned_name,
                clan_name.strip() if clan_name else None,
                gender.strip() if gender else None,
                birth_year,
                notes.strip() if notes else None,
                father_id,
                mother_id,
            ),
        )
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
                father.full_name AS father_name,
                mother.full_name AS mother_name
            FROM people AS child
            LEFT JOIN people AS father ON father.id = child.father_id
            LEFT JOIN people AS mother ON mother.id = child.mother_id
            WHERE child.full_name = ?
            """,
            (full_name.strip(),),
        )
        return cursor.fetchone()

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


class ClanBookApp:
    def __init__(self, root: tk.Tk, book: ClanBook) -> None:
        self.root = root
        self.book = book
        self.selected_name: str | None = None

        self.root.title("Clan Book")
        self.root.geometry("1100x700")
        self.root.minsize(950, 620)

        self.full_name_var = tk.StringVar()
        self.clan_name_var = tk.StringVar()
        self.gender_var = tk.StringVar()
        self.birth_year_var = tk.StringVar()
        self.father_name_var = tk.StringVar()
        self.mother_name_var = tk.StringVar()

        self._configure_style()
        self._build_layout()
        self.refresh_people()

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

        title = ttk.Label(
            outer,
            text="Clan Book",
            style="Title.TLabel",
            font=("Georgia", 24, "bold"),
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            outer,
            text="Register clan members and trace each person's family chain.",
            style="Title.TLabel",
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(4, 14))

        content = ttk.Frame(outer, style="App.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        left = ttk.Frame(content, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(content, style="App.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_form(left)
        self._build_people_list(left)
        self._build_details_panel(right)
        self._build_lineage_panel(right)

    def _build_form(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Register Person", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        fields = [
            ("Full name", self.full_name_var),
            ("Clan name", self.clan_name_var),
            ("Gender", self.gender_var),
            ("Birth year", self.birth_year_var),
            ("Father full name", self.father_name_var),
            ("Mother full name", self.mother_name_var),
        ]

        for row_index, (label, variable) in enumerate(fields, start=1):
            ttk.Label(card, text=label, style="Body.TLabel").grid(
                row=row_index, column=0, sticky="w", padx=(0, 12), pady=6
            )
            ttk.Entry(card, textvariable=variable).grid(
                row=row_index, column=1, sticky="ew", pady=6
            )

        ttk.Label(card, text="Notes", style="Body.TLabel").grid(
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

        ttk.Button(
            button_row,
            text="Save Person",
            style="Accent.TButton",
            command=self.save_person,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Clear Form",
            command=self.clear_form,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_people_list(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=1, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        ttk.Label(card, text="Registered People", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        self.people_listbox = tk.Listbox(
            card,
            activestyle="none",
            font=("Segoe UI", 10),
            bg="#fffdf8",
            fg="#2c2419",
            selectbackground="#b5873f",
            selectforeground="#ffffff",
        )
        self.people_listbox.grid(row=1, column=0, sticky="nsew")
        self.people_listbox.bind("<<ListboxSelect>>", self.on_person_selected)

        scrollbar = ttk.Scrollbar(
            card, orient="vertical", command=self.people_listbox.yview
        )
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.people_listbox.config(yscrollcommand=scrollbar.set)

    def _build_details_panel(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        ttk.Label(card, text="Person Details", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        self.details_text = tk.Text(
            card,
            height=12,
            wrap="word",
            font=("Consolas", 10),
            bg="#fffdf8",
            fg="#2c2419",
            state="disabled",
        )
        self.details_text.grid(row=1, column=0, sticky="nsew")

    def _build_lineage_panel(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=1, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        top = ttk.Frame(card, style="Card.TFrame")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(0, weight=1)

        ttk.Label(top, text="Family Chain", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        ttk.Button(top, text="Show Selected Lineage", command=self.show_lineage).grid(
            row=0, column=1, sticky="e"
        )

        self.lineage_text = tk.Text(
            card,
            height=12,
            wrap="word",
            font=("Consolas", 10),
            bg="#fffdf8",
            fg="#2c2419",
            state="disabled",
        )
        self.lineage_text.grid(row=1, column=0, sticky="nsew")

    def set_text(self, widget: tk.Text, value: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.config(state="disabled")

    def refresh_people(self) -> None:
        current_selection = self.selected_name
        self.people_listbox.delete(0, tk.END)

        people = list(self.book.list_people())
        for person in people:
            self.people_listbox.insert(tk.END, person["full_name"])

        if not people:
            self.selected_name = None
            self.set_text(self.details_text, "No people have been registered yet.")
            self.set_text(self.lineage_text, "Select a person to see their family chain.")
            return

        if current_selection:
            names = [person["full_name"] for person in people]
            if current_selection in names:
                index = names.index(current_selection)
                self.people_listbox.selection_set(index)
                self.people_listbox.activate(index)
                self.people_listbox.see(index)
                self.show_person(current_selection)
                return

        self.people_listbox.selection_set(0)
        self.people_listbox.activate(0)
        self.on_person_selected()

    def save_person(self) -> None:
        birth_year_text = self.birth_year_var.get().strip()
        birth_year = None
        if birth_year_text:
            if not birth_year_text.isdigit():
                messagebox.showerror("Invalid birth year", "Birth year must be a number.")
                return
            birth_year = int(birth_year_text)

        try:
            self.book.add_person(
                full_name=self.full_name_var.get(),
                clan_name=self.clan_name_var.get() or None,
                gender=self.gender_var.get() or None,
                birth_year=birth_year,
                notes=self.notes_text.get("1.0", tk.END).strip() or None,
                father_name=self.father_name_var.get() or None,
                mother_name=self.mother_name_var.get() or None,
            )
        except ValueError as error:
            messagebox.showerror("Cannot save person", str(error))
            return
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Cannot save person",
                "That person already exists in the clan book.",
            )
            return

        saved_name = self.full_name_var.get().strip()
        self.clear_form()
        self.selected_name = saved_name
        self.refresh_people()
        self.show_person(saved_name)
        self.show_lineage()
        messagebox.showinfo("Saved", f"{saved_name} was added successfully.")

    def clear_form(self) -> None:
        self.full_name_var.set("")
        self.clan_name_var.set("")
        self.gender_var.set("")
        self.birth_year_var.set("")
        self.father_name_var.set("")
        self.mother_name_var.set("")
        self.notes_text.delete("1.0", tk.END)

    def on_person_selected(self, _event: object | None = None) -> None:
        selection = self.people_listbox.curselection()
        if not selection:
            return

        name = self.people_listbox.get(selection[0])
        self.show_person(name)
        self.show_lineage()

    def show_person(self, full_name: str) -> None:
        details = self.book.get_person_details(full_name)
        if not details:
            self.selected_name = None
            self.set_text(self.details_text, "Person not found.")
            return

        self.selected_name = full_name
        details_output = "\n".join(
            [
                f"Name: {details['full_name']}",
                f"Clan: {details['clan_name'] or 'Not set'}",
                f"Gender: {details['gender'] or 'Not set'}",
                f"Birth year: {details['birth_year'] or 'Not set'}",
                f"Father: {details['father_name'] or 'Unknown'}",
                f"Mother: {details['mother_name'] or 'Unknown'}",
                f"Notes: {details['notes'] or 'None'}",
            ]
        )
        self.set_text(self.details_text, details_output)

    def show_lineage(self) -> None:
        if not self.selected_name:
            self.set_text(self.lineage_text, "Select a person to see their family chain.")
            return

        try:
            lineage_output = "\n".join(self.book.lineage(self.selected_name))
        except ValueError as error:
            lineage_output = str(error)

        self.set_text(self.lineage_text, lineage_output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register clan members and trace their family chain."
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Register a new person.")
    add_parser.add_argument("--name", required=True, help="Full name of the person.")
    add_parser.add_argument("--clan", help="Clan name.")
    add_parser.add_argument("--gender", help="Gender.")
    add_parser.add_argument("--birth-year", type=int, help="Birth year.")
    add_parser.add_argument("--notes", help="Extra notes.")
    add_parser.add_argument("--father", help="Full name of the father.")
    add_parser.add_argument("--mother", help="Full name of the mother.")

    subparsers.add_parser("list", help="List all registered people.")

    details_parser = subparsers.add_parser("details", help="Show one person's details.")
    details_parser.add_argument("--name", required=True, help="Full name to search.")

    lineage_parser = subparsers.add_parser(
        "lineage", help="Show the full parent chain for a person."
    )
    lineage_parser.add_argument("--name", required=True, help="Full name to search.")

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
                birth_year=args.birth_year,
                notes=args.notes,
                father_name=args.father,
                mother_name=args.mother,
            )
            print(f"Registered {args.name}.")
        elif args.command == "list":
            people = list(book.list_people())
            if not people:
                print("No people have been registered yet.")
                return
            for person in people:
                print(person["full_name"])
        elif args.command == "details":
            details = book.get_person_details(args.name)
            if not details:
                raise ValueError(f"'{args.name}' was not found in the clan book.")
            print(f"Name: {details['full_name']}")
            print(f"Clan: {details['clan_name'] or 'Not set'}")
            print(f"Gender: {details['gender'] or 'Not set'}")
            print(f"Birth year: {details['birth_year'] or 'Not set'}")
            print(f"Father: {details['father_name'] or 'Unknown'}")
            print(f"Mother: {details['mother_name'] or 'Unknown'}")
            print(f"Notes: {details['notes'] or 'None'}")
        elif args.command == "lineage":
            for line in book.lineage(args.name):
                print(line)
    finally:
        if args.command:
            book.close()


if __name__ == "__main__":
    main()
