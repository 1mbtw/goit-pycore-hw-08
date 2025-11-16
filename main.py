#!/usr/bin/env python3

from collections import UserDict
from datetime import datetime, date, timedelta
import pickle  # <-- добавили для сериализации


# ========================= МОДЕЛІ =========================

class Field:
    """Базове поле запису"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """Обов’язкове поле — ім’я контакту"""
    def __init__(self, value):
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        super().__init__(value)


class Phone(Field):
    """Поле телефону. Перевірка: 10 цифр"""
    def __init__(self, value):
        if not value.isdigit() or len(value) != 10:
            raise ValueError("Phone must contain 10 digits.")
        super().__init__(value)


class Birthday(Field):
    # формат DD.MM.YYYY
    def __init__(self, value):
        try:
            dt = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(dt.strftime("%d.%m.%Y"))

    def as_date(self):
        return datetime.strptime(self.value, "%d.%m.%Y").date()


class Record:
    """Запис контакту: ім’я + телефони"""
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None  # може бути тільки одне

    """Додати телефон"""
    def add_phone(self, phone):
        self.phones.append(Phone(phone))
        
    """Видалити телефон"""
    def remove_phone(self, phone):
        for p in self.phones:
            if p.value == phone:
                self.phones.remove(p)
                return True
        return False

    """Редагувати існуючий телефон"""
    def edit_phone(self, old_phone, new_phone):
        for p in self.phones:
            if p.value == old_phone:
                p.value = Phone(new_phone).value
                return True
        return False

    """Пошук телефону в записі"""
    def find_phone(self, phone):
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    """Додавання дня народження"""
    def add_birthday(self, birthday_text):
        self.birthday = Birthday(birthday_text)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones) if self.phones else "-"
        bday = self.birthday.value if self.birthday else "-"

        return f"Contact name: {self.name.value}, phones: {phones}, birthday: {bday}"


class AddressBook(UserDict):
    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def delete(self, name):
        return self.data.pop(name, None) is not None

    # адаптація функції з тижня 
    def get_upcoming_birthdays(self):
        today = date.today()
        end_day = today + timedelta(days=7)
        result = {}

        for record in self.data.values():
            if not record.birthday:
                continue

            bday = record.birthday.as_date()
            bday_this_year = date(today.year, bday.month, bday.day)

            # якщо вже був у цьому році — дивимось наступний
            if bday_this_year < today:
                bday_this_year = date(today.year + 1, bday.month, bday.day)

            # в межах наступних 7 днів
            if today <= bday_this_year < end_day:
                congratulation_day = bday_this_year

                # якщо вихідні — переносимо на понеділок
                if congratulation_day.weekday() == 5:      # Saturday
                    congratulation_day += timedelta(days=2)
                elif congratulation_day.weekday() == 6:    # Sunday
                    congratulation_day += timedelta(days=1)

                weekday = congratulation_day.strftime("%A")
                result.setdefault(weekday, []).append(record.name.value)

        return result


# ========================= ЗБЕРЕЖЕННЯ / ЗАВАНТАЖЕННЯ ===================

def save_data(book: AddressBook, filename: str = "addressbook.pkl"):
    """Серіалізація адресної книги на диск."""
    with open(filename, "wb") as f:
        pickle.dump(book, f)


def load_data(filename: str = "addressbook.pkl") -> AddressBook:
    """
    Десеріалізація адресної книги з диска.
    Якщо файл не знайдено — повертаємо нову AddressBook.
    """
    try:
        with open(filename, "rb") as f:
            book = pickle.load(f)
            # на всякий случай убеждаемся, что это AddressBook
            if isinstance(book, AddressBook):
                return book
            return AddressBook()
    except FileNotFoundError:
        return AddressBook()


# ========================= інфраструктура ===================

def input_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            return "Contact not found."
        except ValueError as e:
            # тут і про телефон, і про дату
            msg = str(e) if str(e) else "Give me correct data please."
            return msg
        except IndexError:
            return "Enter the argument for the command"
    return inner


def parse_input(user_input: str):
    user_input = user_input.strip()
    if not user_input:
        return "", []
    parts = user_input.split()
    cmd = parts[0].lower()
    args = parts[1:]
    return cmd, args


def help_text() -> str:
    return (
        "Available commands:\n"
        "  hello                         -> How can I help you?\n"
        "  add <name> <phone>            -> add new contact or phone to existing\n"
        "  change <name> <old> <new>     -> change phone for contact\n"
        "  phone <name>                  -> show phones of contact\n"
        "  all                           -> list all contacts\n"
        "  add-birthday <name> <date>    -> set birthday (DD.MM.VYYY)\n"
        "  show-birthday <name>          -> show birthday of contact\n"
        "  birthdays                     -> show birthdays for next week\n"
        "  help                          -> show this help\n"
        "  close | exit                  -> quit"
    )


# ========================= ОБРОБНИКИ =========================

@input_error
def add_contact(args, book: AddressBook):
    #: name, phone, *_ = args
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_contact(args, book: AddressBook):
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if record.edit_phone(old_phone, new_phone):
        return "Contact updated."
    return "Old phone not found."


@input_error
def show_phone(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return "No phones."
    return "; ".join(p.value for p in record.phones)


@input_error
def show_all(book: AddressBook):
    if not book.data:
        return "No contacts yet."
    lines = []
    for record in book.data.values():
        lines.append(str(record))
    return "\n".join(lines)


# ----------------------------------------

@input_error
def add_birthday(args, book: AddressBook):
    name, birthday_text, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
    record.add_birthday(birthday_text)
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if record.birthday:
        return record.birthday.value
    return "No birthday set."


@input_error
def birthdays(args, book: AddressBook):
    plan = book.get_upcoming_birthdays()
    if not plan:
        return "No birthdays next week."
    # виведемо по днях
    result_lines = []
    # щоб було у порядку днів
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days_order:
        if day in plan:
            names = ", ".join(plan[day])
            result_lines.append(f"{day}: {names}")
    return "\n".join(result_lines)


# ========================= MAIN =========================

def main():
    # При запуску програми пробуем загрузить существующую книгу
    book = load_data()

    print("Welcome to the assistant bot!")
    print('Type "help" to see commands.')

    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
            # Перед выходом сохраняем все изменения
            save_data(book)
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "help":
            print(help_text())

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_contact(args, book))

        elif command == "phone":
            print(show_phone(args, book))

        elif command == "all":
            print(show_all(book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        elif command == "":
            # порожній ввід — нічого не робимо
            continue

        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
