import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor


class LibraryDB:
    def __init__(self, dbname='library_db', user='postgres', password='78nalodo', host='localhost'):
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host
        )
        self.cursor = self.conn.cursor(cursor_factory=DictCursor)
        print("Подключение к БД успешно!")

    def close(self):
        self.cursor.close()
        self.conn.close()
        print("Подключение закрыто.")

    def execute_query(self, query, params=None):
        """Универсальный метод выполнения SQL-запросов"""
        try:
            self.cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                return self.cursor.fetchall()
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка выполнения запроса: {e}")
            return None

    def insert(self, table, data):
        """Упрощенный метод для вставки данных"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute_query(query, tuple(data.values()))

    def get_reader_id_by_name(self, name):
        """Поиск читателей по ФИО"""
        query = "SELECT код_читателя, фио FROM читатели WHERE фио ILIKE %s"
        return self.execute_query(query, (f"%{name}%",))

    def get_author_id_by_name(self, name):
        """Поиск автора по ФИО"""
        query = "SELECT код_автора FROM авторы WHERE фио = %s"
        result = self.execute_query(query, (name,))
        return result[0][0] if result else None

    def get_available_books(self):
        """Список доступных книг"""
        query = "SELECT код_книги, название FROM книги WHERE количество > 0"
        return self.execute_query(query)

    def get_themes_list(self):
        """Список всех тематик"""
        return self.execute_query("SELECT код_тематики, наименование FROM тематики")

    def add_theme(self, name):
        """Добавление новой тематики"""
        return self.insert("тематики", {"наименование": name})

    def issue_book(self, library_id, book_id, reader_id, return_date):
        """Выдача книги читателю"""
        return self.insert("абонемент", {
            "код_библиотеки": library_id,
            "код_книги": book_id,
            "код_читателя": reader_id,
            "дата_возврата": return_date
        })

    def find_book_by_title(self, title):
        """Поиск книги по точному названию"""
        query = "SELECT код_книги, код_библиотеки, название FROM книги WHERE название = %s AND количество > 0"
        return self.execute_query(query, (title,))

    def search_books_by_title(self, search_term):
        """Поиск книг по части названия"""
        query = "SELECT код_книги, код_библиотеки, название FROM книги WHERE название ILIKE %s AND количество > 0"
        return self.execute_query(query, (f"%{search_term}%",))

    def get_all_books_info(self):
        """Полная информация о книгах"""
        query = """
            SELECT к.код_книги, к.название, а.фио, т.наименование, к.количество 
            FROM книги к
            JOIN авторы а ON к.код_автора = а.код_автора
            JOIN тематики т ON к.код_тематики = т.код_тематики
        """
        return self.execute_query(query)

    def get_overdue_books(self):
        """Список просроченных книг"""
        return self.execute_query("SELECT * FROM просроченные_книги")


def show_menu():
    """Отображение главного меню"""
    print("\n=== Библиотека ===")
    print("1. Добавить книгу")
    print("2. Показать все книги")
    print("3. Выдать книгу читателю")
    print("4. Показать просроченные книги")
    print("5. Добавить автора")
    print("6. Добавить тематику")
    print("7. Добавить читателя")
    print("8. Выход")


def select_theme(db):
    """Выбор тематики"""
    themes = db.get_themes_list()
    if not themes:
        print("Нет доступных тематик!")
        return None

    print("\nДоступные тематики:")
    for i, theme in enumerate(themes, 1):
        print(f"{i}. {theme[1]}")

    print("\n0. Добавить новую тематику")
    choice = input("Выберите номер: ")

    if choice == "0":
        name = input("Введите название тематики: ").strip()
        if name and db.add_theme(name):
            print("Тематика добавлена!")
            return len(themes) + 1
        return None

    try:
        return themes[int(choice) - 1][0]
    except (ValueError, IndexError):
        print("Неверный выбор!")
        return None


def select_book(db):
    """Выбор книги"""
    title = input("Введите название книги: ").strip()
    if not title:
        print("Название не может быть пустым!")
        return None

    # Сначала ищем точное совпадение
    books = db.find_book_by_title(title)
    if not books:
        # Если нет точного совпадения, ищем похожие
        books = db.search_books_by_title(title)
        if not books:
            print("Книги не найдены!")
            return None

        print("\nНайдены похожие книги:")
        for i, book in enumerate(books, 1):
            print(f"{i}. {book[2]}")

        choice = input("Выберите номер книги: ")
        try:
            return books[int(choice) - 1]
        except (ValueError, IndexError):
            print("Неверный выбор!")
            return None

    return books[0]


def select_reader(db):
    """Выбор читателя"""
    name = input("Введите ФИО читателя: ").strip()
    if not name:
        print("ФИО не может быть пустым!")
        return None

    readers = db.get_reader_id_by_name(name)
    if not readers:
        print("Читатель не найден!")
        return None

    if len(readers) == 1:
        return readers[0][0]

    print("\nНайдено несколько читателей:")
    for i, reader in enumerate(readers, 1):
        print(f"{i}. {reader[1]}")

    choice = input("Выберите номер: ")
    try:
        return readers[int(choice) - 1][0]
    except (ValueError, IndexError):
        print("Неверный выбор!")
        return None


def main():
    db = LibraryDB(user='postgres', password='78nalodo')

    while True:
        show_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            # Добавление книги
            title = input("Название книги: ").strip()
            if not title:
                print("Название не может быть пустым!")
                continue

            author = input("ФИО автора: ").strip()
            if not author:
                print("ФИО автора не может быть пустым!")
                continue

            author_id = db.get_author_id_by_name(author)
            if author_id is None:
                print("Автор не найден. Добавим нового.")
                country = input("Страна автора: ").strip()
                if db.insert("авторы", {"фио": author, "страна": country}):
                    author_id = db.get_author_id_by_name(author)

            theme_id = select_theme(db)
            if not theme_id:
                continue

            publisher = input("Издательство: ").strip()
            place = input("Место издания: ").strip()
            year = input("Год издания: ").strip()
            count = input("Количество: ").strip() or "1"

            book_data = {
                "код_библиотеки": 1,
                "код_тематики": theme_id,
                "код_автора": author_id,
                "название": title,
                "издательство": publisher,
                "место_издания": place,
                "год": year,
                "количество": count
            }

            if db.insert("книги", book_data):
                print("Книга успешно добавлена!")

        elif choice == "2":
            books = db.get_all_books_info()
            if books:
                print("\nСписок книг:")
                for book in books:
                    print(f"{book[0]}: {book[1]} ({book[2]}, {book[3]}) - {book[4]} шт.")
            else:
                print("Книги не найдены!")

        elif choice == "3":
            book = select_book(db)
            if not book:
                continue

            reader_id = select_reader(db)
            if not reader_id:
                continue

            date = input("Дата возврата (ГГГГ-ММ-ДД): ").strip()
            if db.issue_book(book[1], book[0], reader_id, date):
                print("Книга выдана!")

        elif choice == "4":
            books = db.get_overdue_books()
            if books:
                print("\nПросроченные книги:")
                for book in books:
                    print(book)
            else:
                print("Просроченных книг нет")

        elif choice == "5":
            name = input("ФИО автора: ").strip()
            if not name:
                print("ФИО не может быть пустым!")
                continue

            country = input("Страна: ").strip()
            if db.insert("авторы", {"фио": name, "страна": country}):
                print("Автор добавлен!")

        elif choice == "6":
            name = input("Название тематики: ").strip()
            if not name:
                print("Название не может быть пустым!")
                continue

            if db.add_theme(name):
                print("Тематика добавлена!")

        elif choice == "7":
            name = input("ФИО читателя: ").strip()
            if not name:
                print("ФИО не может быть пустым!")
                continue

            address = input("Адрес: ").strip()
            phone = input("Телефон: ").strip()
            if db.insert("читатели", {"фио": name, "адрес": address, "телефон": phone}):
                print("Читатель добавлен!")

        elif choice == "8":
            break

        else:
            print("Неверный выбор!")

    db.close()


if __name__ == "__main__":
    main()