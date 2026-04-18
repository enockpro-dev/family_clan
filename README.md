# Clan Book

A small Python desktop app for registering clan members.

## Features

- Register a person with clan details in a desktop window
- Save records in SQLite so the data stays after closing the app
- Link each person to a father and mother
- Still supports command line actions if needed

## Run the desktop app

```powershell
python clan_book.py
```

The window includes:

1. A registration form only
2. Fields for name, clan, gender, parents, and notes
3. Save and clear buttons

## Command line examples

Add a person:

```powershell
python clan_book.py add --name "John Okello" --clan "Lion" --gender "Male"
```

Add a child and connect the father:

```powershell
python clan_book.py add --name "Peter Okello" --father "John Okello"
```

## Notes

- Add parents first before linking them to a child
- The database file is created automatically as `clan_book.db`
- Tkinter usually comes with Python on Windows
- The desktop form does not ask for birth information
