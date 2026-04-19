# Clan Book

A small Python desktop app for a family clan system.

## Features

- Register a person with clan details in a desktop window
- Front view with login or register choices
- Logged-in users can search another registered person and see the relationship
- Save records in SQLite so the data stays after closing the app
- Link each person to a father and mother
- Still supports command line actions if needed

## Run the desktop app

```powershell
python clan_book.py
```

The window includes:

1. A front view as the first screen
2. A front view with `Login` or `Register`
3. Login checks whether the person already exists
4. Register opens the person details form
5. After login, a user can search another registered person and see the relationship

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

- The database file is created automatically as `clan_book.db`
- Tkinter usually comes with Python on Windows
- The desktop form does not ask for birth information
- The register form uses first name, second name, clan name, gender, parents, and notes
- A person can register even if the parents are not yet saved in the system
- When a matching parent is later registered, the app can link that relationship automatically
- Relationship search works best when family members are registered and linked in the system
