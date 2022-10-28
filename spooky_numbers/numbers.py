from __future__ import annotations

import contextlib
import itertools
import os
import socket
import random
import datetime
import time
from types import TracebackType
from PIL import Image, ImageOps
import unidecode

import flask

from spooky_numbers import db

blueprint = flask.Blueprint("numbers", __name__)

NUMBERS_LINES = 3
NUMBERS_COLUMNS = 2
TOTAL_NUMBERS = NUMBERS_LINES * NUMBERS_COLUMNS

RANDOM_NUMBERS_POPULATION = [n for n in range(100, 10_000)]

MAX_NUMBER = 999_999_999

LOCATIONS = [
    "Planning Bureau",
    "Beichtstuhl",
    "Satans Office",
    "Dancefloor",
    "Kitchen",
    "drink a shot",
    "Buttock Enlargement",
]

def numbers_from_db():
    results = db.get_db().execute(
        """
        SELECT numbers.id, person.number, numbers.location 
        FROM numbers JOIN person ON person.id = numbers.person_id
        """
    ).fetchall()
    return [tuple(row) for row in results]

def insert_number(person_id, location):
    db.get_db().execute(f"INSERT INTO numbers (person_id, location) VALUES ({person_id}, '{location}')")
    db.get_db().commit()

def delete_number(number_id):
    db.get_db().execute(f"DELETE FROM numbers WHERE id={number_id}")
    db.get_db().commit()

def insert_person(name, number):
    db.get_db().execute(f"INSERT INTO person (name, number) VALUES ('{name}', {number})")
    db.get_db().commit()

def get_persons():
    results = db.get_db().execute(
        """
        SELECT person.id, person.name, person.number 
        FROM person
        ORDER BY person.name, person.number
        """
    ).fetchall()
    return [tuple(row) for row in results]

@blueprint.route("/")
def screen():
    numbers = numbers_from_db()
    _, db_numbers, locations = zip(*numbers) if numbers else (None, [], [])

    all_numbers = list(db_numbers)# + list(random.choices(RANDOM_NUMBERS_POPULATION, k=TOTAL_NUMBERS - len(db_numbers)))

    numbers_padded = [
        f"{n:06}"
        for n in all_numbers
    ]

    numbers_formatted = [
        "-".join(number[i:i+3] for i in range(0, len(number), 3))
        for number in numbers_padded
    ]

    all_locations = list(locations)# + list(random.choices(LOCATIONS, k=TOTAL_NUMBERS - len(db_numbers)))

    refresh_after = 10


    numbers = list(zip(numbers_formatted, all_locations))
    sorted(numbers)

    return flask.render_template(
        "numbers.html", 
        refresh_after=refresh_after, 
        numbers=numbers,
    )

@blueprint.route("/admin")
def admin():
    current_numbers = numbers_from_db()
    persons = get_persons()
    return flask.render_template(
        "admin.html",
        current_numbers=current_numbers,
        persons=persons,
        locations=LOCATIONS,
        can_add=can_add_number(),
    )

@blueprint.route("/register")
def register():
    return flask.render_template(
        "register.html",
    )

def can_add_number():
    return len(numbers_from_db()) < TOTAL_NUMBERS

@blueprint.route("/number", methods=["POST"])
def number():
    if not can_add_number():
        return flask.redirect("/admin")
    person_id = flask.request.form["person_id"]
    location = flask.request.form["location"]

    try:
        person_id = int(person_id)
    except ValueError:
        return "Person ID not an int", 400
    if not location or not isinstance(location, str):
        return "Bad location", 400

    insert_number(person_id, location)

    return flask.redirect("/admin")

@blueprint.route("/delete_number", methods=["POST"])
def delete_number_route():
    number_id_text = flask.request.form["number_id"]

    try:
        number_id = int(number_id_text)
    except ValueError:
        return "Number ID not an int", 400

    delete_number(number_id)

    return flask.redirect("/admin")


class Printer(contextlib.AbstractContextManager):
    """
    [instruction]*;[message]\n


    Instructions:
        B: Bold ON
        b: Bold OFF
        L: Justify L
        C: Justify C
        R: Justify R
        s: Size S
        m: Size M
        l: Size L
        I: Inverse ON
        i: Inverse OFF
        U: Underline ON
        u: Underline OFF
        D: Double Height ON
        d: Double Height OFF
        E: End Message
    """
    ARDUINO_IP = "192.168.2.142"
    ARDUINO_PORT = 5000

    IMAGE_SIZE = 384
    assert IMAGE_SIZE % 8 == 0
    MAX_BYTES = 1024

    def __init__(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def __enter__(self) -> Printer:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.ARDUINO_IP, self.ARDUINO_PORT))
        self.bold_off()
        self.justify_left()
        self.size_medium()
        self.inverse_off()
        return self
    
    def __exit__(self, __exc_type: type[BaseException] | None, __exc_value: BaseException | None, __traceback: TracebackType | None) -> bool | None:
        self.end_file()
        self._socket.close()
        return super().__exit__(__exc_type, __exc_value, __traceback)
    
    @staticmethod
    def _command(char: bytes) -> callable[[Printer], None]:
        assert len(char) == 1
        def command(self: Printer) -> None:
            self.send_raw(char)
        return command
    
    bold_on = _command(b"B")
    bold_off = _command(b"b")
    justify_left = _command(b"L")
    justify_center = _command(b"C")
    justify_right = _command(b"R")
    size_small = _command(b"s")
    size_medium = _command(b"m")
    size_large = _command(b"l")
    inverse_on = _command(b"I")
    inverse_off = _command(b"i")

    @staticmethod
    def str_to_bytes(s: str) -> bytes:
        return bytes(unidecode.unidecode(s), encoding="ascii")

    def end_file(self) -> None:
        self.send_raw(b"E")

    def send_raw(self, data: bytes) -> None:
        self._socket.sendall(data)
    
    def send_str(self, data: str) -> None:
        self.send_raw(self.str_to_bytes(data))
    
    def print_line(self, line: str) -> None:
        for sub_line in line.split("\n"):
            self.send_str(f";{sub_line}")
            self.send_raw(b"\n")
    
    @staticmethod
    def _calibrate_colors(image: Image) -> Image:
        image = image.convert("L")
        pixels = image.load()
        all_pixels = [pixels[x, y] for x, y in itertools.product(range(image.width), range(image.height))]
        min_pixel = min(all_pixels)
        max_pixel = max(all_pixels)
        pixel_range = max_pixel - min_pixel
        if pixel_range <= 1:
            return image
        for x, y in itertools.product(range(image.width), range(image.height)):
            pixels[x, y] = int((pixels[x, y] - min_pixel) * 256 / pixel_range)
        return image


    def print_image(self, filename: str, calibrate_colors: bool=False) -> None:
        image = Image.open(filename)

        width = image.width
        height = image.height
        ratio = self.IMAGE_SIZE / width
        width = round(width * ratio)
        height = round(height * ratio)
        image = image.resize((width, height))

        if calibrate_colors:
            self._calibrate_colors(image)

        image = image.convert("1")
        image = ImageOps.invert(image)

        image_data = image.tobytes()

        bytes_per_line = width // 8
        lines_per_chunk = self.MAX_BYTES // bytes_per_line
        chunk_size = bytes_per_line * lines_per_chunk

        chunks = (
            image_data[i:i+chunk_size]
            for i in range(0, len(image_data), chunk_size)
        )
        for chunk in chunks:
            self.send_str(f":{width} {len(chunk) * 8 // width} ")
            self.send_raw(chunk)
            time.sleep(0.5)


@blueprint.route("/print", methods=["POST"])
def print_number():
    name = flask.request.form["name"]
    pronouns = flask.request.form["pronouns"]
    spirit_animal = flask.request.form["spirit_animal"]
    persons = get_persons()
    if persons:
        _, _, numbers = zip(*get_persons())
    else:
        numbers = []
    used_numbers = set(numbers)

    while True:
        number = random.randint(0, 999_999)
        if number not in used_numbers:
            break

    insert_person(name, number)

    redirect_url = flask.url_for(".print_number2", name=name, pronouns=pronouns, spirit_animal=spirit_animal, number=number)
    return flask.render_template("printer_redirect.html", redirect_url=redirect_url)

@blueprint.route("/print2", methods=["GET"])
def print_number2():
    import stability_sdk.client as ai_client
    import mimetypes

    import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
    from google.protobuf.json_format import MessageToDict


    name = flask.request.args["name"]
    spirit_animal = flask.request.args["spirit_animal"]
    pronouns = flask.request.args["pronouns"]
    number = f"{int(flask.request.args['number']):06}"
    number = f"{number[:3]}-{number[3:]}"
    
    if pronouns.lower() == "he/him":
        gender_expression = "masculine"
    elif pronouns.lower() == "she/her":
        gender_expression = "feminine"
    else:
        gender_expression = "androgynous"


    host = "grpc.stability.ai:443"

    # Get an API key at https://stability.ai/
    # Usage is free up to a point.
    api_key = ""

    stability_api = ai_client.StabilityInference(host, api_key)

    now = datetime.datetime.now()
    images_dir = os.path.join(os.path.dirname(__file__), "static", "images")
    file_name = now.isoformat()
    full_path = os.path.join(images_dir, file_name)

    prompt = f"An illustration of a {gender_expression} demon in the shape of a {spirit_animal} by louis le breton from the dictionnaire infernal"

    good_image = False
    while not good_image:
        good_image = True
        answers = stability_api.generate(prompt, width=512, height=512)

        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.type == generation.ARTIFACT_TEXT:
                    contents = MessageToDict(artifact)
                    action = contents.get("realizedAction")
                    if action != "ACTION_PASSTHROUGH":
                        good_image = False
                elif artifact.type != generation.ARTIFACT_IMAGE:
                    continue
                ext = mimetypes.guess_extension(artifact.mime)
                contents = artifact.binary
                image_path = f"{full_path}{ext}"
                with open(image_path, "wb") as f:
                    f.write(bytes(contents))

    with Printer() as printer:
        printer.justify_center()
        printer.bold_on()
        printer.size_large()
        printer.print_line("Welcome")
        printer.print_line(name)
        printer.size_medium()
        printer.print_line(f"({pronouns})")
        printer.print_line("")
        printer.size_medium()
        printer.bold_off()
        printer.print_line("Your ticket number:")
        printer.print_line("")
        printer.inverse_on()
        printer.bold_on()
        printer.size_large()
        printer.print_line(number)
        printer.print_line("")
        printer.inverse_off()
        printer.size_small()
        printer.print_line("A personal demon has been\nassigned to you:")
        printer.print_image(image_path, calibrate_colors=True)
        printer.size_large()
        printer.print_line("")
        printer.print_line("")
        printer.print_line("")
        printer.print_line("")
        printer.print_line("")
        printer.print_line("")
        printer.print_line("")
        printer.print_line("")

    return flask.redirect(flask.url_for(".register"))
