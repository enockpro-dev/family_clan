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
                None,
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

        self.root.title("Clan Registration")
        self.root.geometry("760x560")
        self.root.minsize(680, 520)

        self.login_name_var = tk.StringVar()
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
            text="Family Clan Book",
            style="Title.TLabel",
            font=("Georgia", 24, "bold"),
        )
        self.header_title.pack(anchor="w")

        self.header_subtitle = ttk.Label(
            outer,
            text="Choose login if already registered, or register to create a new record.",
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
        self.header_title.config(text="Family Clan Book")
        self.header_subtitle.config(
            text="Choose login if already registered, or register to create a new record."
        )

        card = ttk.Frame(self.content, style="Card.TFrame", padding=24)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Welcome", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        message = (
            "This is the front view of the family clan app.\n"
            "Select login if the person is already registered,\n"
            "or select register for a new person."
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
            text="Login",
            style="Accent.TButton",
            command=self.show_login_view,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Register",
            command=self.show_register_view,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def show_login_view(self) -> None:
        self._clear_content()
        self.header_title.config(text="Login")
        self.header_subtitle.config(
            text="Enter the person's full name to continue if they are already registered."
        )

        card = ttk.Frame(self.content, style="Card.TFrame", padding=24)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Login", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )
        ttk.Label(card, text="Full name", style="Body.TLabel").grid(
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
            text="Continue",
            style="Accent.TButton",
            command=self.login_person,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Back",
            command=self.show_home_view,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def show_register_view(self) -> None:
        self._clear_content()
        self.header_title.config(text="Register")
        self.header_subtitle.config(
            text="Enter a person's details to register them in the clan book."
        )
        self._build_form(self.content)

    def _build_form(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Registration Form", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        fields = [
            ("First name", self.first_name_var),
            ("Second name", self.second_name_var),
            ("Clan name", self.clan_name_var),
            ("Gender", self.gender_var),
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
            row=6, column=0, sticky="nw", padx=(0, 12), pady=6
        )
        self.notes_text = tk.Text(
            card,
            height=4,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#2c2419",
        )
        self.notes_text.grid(row=6, column=1, sticky="ew", pady=6)

        button_row = ttk.Frame(card, style="Card.TFrame")
        button_row.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
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
        ).grid(row=0, column=1, sticky="ew", padx=(6, 6))

        ttk.Button(
            button_row,
            text="Back",
            command=self.show_home_view,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

    def login_person(self) -> None:
        full_name = self.login_name_var.get().strip()
        if not full_name:
            messagebox.showerror("Login", "Enter the full name first.")
            return

        person = self.book.get_person_details(full_name)
        if not person:
            messagebox.showerror(
                "Not found",
                f"{full_name} is not registered yet. Please use Register.",
            )
            return

        messagebox.showinfo("Login", f"Welcome back, {full_name}.")
        self.login_name_var.set("")

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
            messagebox.showerror("Cannot save person", str(error))
            return
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Cannot save person",
                "That person already exists in the clan book.",
            )
            return

        self.clear_form()
        messagebox.showinfo("Saved", f"{full_name} was added successfully.")

    def build_full_name(self) -> str:
        first_name = self.first_name_var.get().strip()
        second_name = self.second_name_var.get().strip()
        if not first_name or not second_name:
            raise ValueError("First name and second name are required.")
        return f"{first_name} {second_name}"

    def clear_form(self) -> None:
        self.first_name_var.set("")
        self.second_name_var.set("")
        self.clan_name_var.set("")
        self.gender_var.set("")
        self.father_name_var.set("")
        self.mother_name_var.set("")
        self.notes_text.delete("1.0", tk.END)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register clan members and trace their family chain."
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Register a new person.")
    add_parser.add_argument("--name", required=True, help="Full name of the person.")
    add_parser.add_argument("--clan", help="Clan name.")
    add_parser.add_argument("--gender", help="Gender.")
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
