# Clan Book

A small Python desktop app for registering clan members and showing their family chain.

## Features

- Register a person with clan details in a desktop window
- Save records in SQLite so the data stays after closing the app
- Link each person to a father and mother
- View one person's details
- View the lineage chain of parents and grandparents upward
- Still supports command line actions if needed

## Run the desktop app

```powershell
python clan_book.py
```

The window includes:

1. A form to register a person
2. A list of all registered people
3. A details panel for the selected person
4. A family chain panel showing the selected person's lineage

## Command line examples

Add a person:

```powershell
python clan_book.py add --name "John Okello" --clan "Lion" --gender "Male"
```

Add a child and connect the father:

```powershell
python clan_book.py add --name "Peter Okello" --father "John Okello"
```

Show one person's details:

```powershell
python clan_book.py details --name "Peter Okello"
```

Show lineage:

```powershell
python clan_book.py lineage --name "Peter Okello"
```

List all people:

```powershell
python clan_book.py list
```

## Notes

- Add parents first before linking them to a child
- The database file is created automatically as `clan_book.db`
- Tkinter usually comes with Python on Windows
