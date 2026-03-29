import os


def number_file(service, code):
    return f"numbers/{service}/{code}.txt"


def read_numbers(service, code):

    path = number_file(service, code)

    if not os.path.exists(path):
        return []

    with open(path) as f:
        return [x.strip() for x in f.readlines() if x.strip()]


def save_numbers(service, code, numbers):

    path = number_file(service, code)

    with open(path, "w") as f:
        f.write("\n".join(numbers))


def add_numbers(service, code, new):

    old = read_numbers(service, code)

    numbers = old + new

    save_numbers(service, code, numbers)

    return len(new)
