import difflib
import re
import unicodedata

# (país, alias del país, gentilicio masculino, gentilicio femenino o None si es invariable, alias del gentilicio)
COUNTRIES = [
    ("Argentina", [], "argentino", "argentina", []),
    ("Bolivia", [], "boliviano", "boliviana", []),
    ("Brasil", ["brazil"], "brasileño", "brasileña", ["brasilero", "brasilera"]),
    ("Chile", [], "chileno", "chilena", []),
    ("Colombia", [], "colombiano", "colombiana", []),
    ("Costa Rica", [], "costarricense", None, []),
    ("Cuba", [], "cubano", "cubana", []),
    ("Ecuador", [], "ecuatoriano", "ecuatoriana", []),
    ("El Salvador", ["salvador"], "salvadoreño", "salvadoreña", []),
    ("Guatemala", [], "guatemalteco", "guatemalteca", []),
    ("Haití", [], "haitiano", "haitiana", []),
    ("Honduras", [], "hondureño", "hondureña", []),
    ("México", ["mejico"], "mexicano", "mexicana", ["mejicano", "mejicana"]),
    ("Nicaragua", [], "nicaragüense", None, ["nicaraguense"]),
    ("Panamá", [], "panameño", "panameña", []),
    ("Paraguay", [], "paraguayo", "paraguaya", []),
    ("Perú", [], "peruano", "peruana", []),
    ("Puerto Rico", [], "puertorriqueño", "puertorriqueña", []),
    ("República Dominicana", ["rep dominicana", "rep. dominicana"], "dominicano", "dominicana", []),
    ("Uruguay", [], "uruguayo", "uruguaya", []),
    ("Venezuela", [], "venezolano", "venezolana", []),
    ("España", [], "español", "española", []),
    ("Marruecos", [], "marroquí", None, ["marroqui"]),
    ("Argelia", [], "argelino", "argelina", []),
    ("Senegal", [], "senegalés", "senegalesa", []),
    ("Nigeria", [], "nigeriano", "nigeriana", []),
    ("Ghana", [], "ghanés", "ghanesa", []),
    ("Camerún", [], "camerunés", "camerunesa", []),
    ("Mali", [], "maliense", None, []),
    ("Egipto", [], "egipcio", "egipcia", []),
    ("India", [], "indio", "india", ["hindú"]),
    ("Pakistán", [], "pakistaní", None, ["pakistani"]),
    ("Bangladés", ["bangladesh"], "bangladesí", None, ["bangladeshi"]),
    ("China", [], "chino", "china", []),
    ("Filipinas", [], "filipino", "filipina", []),
    ("Rusia", [], "ruso", "rusa", []),
    ("Ucrania", [], "ucraniano", "ucraniana", []),
    ("Rumanía", ["rumania"], "rumano", "rumana", []),
    ("Bulgaria", [], "búlgaro", "búlgara", []),
    ("Italia", [], "italiano", "italiana", []),
    ("Francia", [], "francés", "francesa", []),
    ("Alemania", [], "alemán", "alemana", []),
    ("Portugal", [], "portugués", "portuguesa", []),
    ("Reino Unido", ["uk", "inglaterra", "gran bretaña"], "británico", "británica", ["ingles", "inglés", "inglesa"]),
    ("Estados Unidos", ["eeuu", "ee.uu", "ee uu", "usa", "us", "estados unidos de america"],
     "estadounidense", None, ["americano", "americana", "norteamericano", "norteamericana"]),
    ("Canadá", [], "canadiense", None, []),
    ("Turquía", [], "turco", "turca", []),
    ("Irán", [], "iraní", None, ["irani"]),
    ("Siria", [], "sirio", "siria", []),
    ("Líbano", [], "libanés", "libanesa", []),
    ("Georgia", [], "georgiano", "georgiana", []),
    ("Armenia", [], "armenio", "armenia", []),
]

LOWERCASE_WORDS = {"de", "del", "la", "las", "los", "y", "e"}
MAX_WORDS = 4
FUZZY_CUTOFF = 0.88  # sube: con 0.82 "Níger" se confundía con "Nigeria"


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))

    return " ".join(re.sub(r"[^\w\s.]", " ", stripped.lower()).split()).strip(".")


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _title(text: str) -> str:
    words = text.strip().split()

    return " ".join(
        word.lower() if index > 0 and word.lower() in LOWERCASE_WORDS else _capitalize(word.lower())
        for index, word in enumerate(words)
    )


# alias (sin tildes ni mayúsculas) -> forma correcta con tildes
_COUNTRY_FORMS: dict[str, str] = {}
_DEMONYM_FORMS: dict[str, str] = {}
# alias de gentilicio o de país -> etiqueta de grupo para estadísticas ("Colombiano/a")
_NATIONALITY_GROUP: dict[str, str] = {}

for _country, _country_aliases, _masculine, _feminine, _demonym_aliases in COUNTRIES:
    _group = f"{_capitalize(_masculine)}/a" if _feminine and _feminine != _masculine else _capitalize(_masculine)

    # setdefault: la forma canónica (con tildes) va primero y no debe pisarla
    # un alias que solo se diferencia en la tilde ("nicaraguense").
    for _alias in [_country, *_country_aliases]:
        _COUNTRY_FORMS.setdefault(_fold(_alias), _country)
        _NATIONALITY_GROUP.setdefault(_fold(_alias), _group)

    for _form in [_masculine, _feminine, *_demonym_aliases]:
        if _form:
            _DEMONYM_FORMS.setdefault(_fold(_form), _capitalize(_form))
            _NATIONALITY_GROUP.setdefault(_fold(_form), _group)


def _exact(text: str, forms: dict[str, str]) -> str | None:
    return forms.get(_fold(text))


def _fuzzy(text: str, forms: dict[str, str]) -> str | None:
    close = difflib.get_close_matches(_fold(text), list(forms), n=1, cutoff=FUZZY_CUTOFF)

    return forms[close[0]] if close else None


def _lookup(text: str, forms: dict[str, str]) -> str | None:
    return _exact(text, forms) or _fuzzy(text, forms)


def _is_short(text: str) -> bool:
    return len(text.split()) <= MAX_WORDS


def normalize_country(text: str) -> str:
    """"peru" -> "Perú", "PERÚ" -> "Perú", "perú" -> "Perú". Lo desconocido solo se limpia."""

    text = " ".join(text.split())

    if not text or not _is_short(text):
        return text

    return _lookup(text, _COUNTRY_FORMS) or _title(text)


def normalize_nationality(text: str) -> str:
    """
    "colombiansa" -> "Colombiana", "peruano" -> "Peruano". Conserva el género
    que escribió la persona; si puso el país en vez del gentilicio, lo deja
    como país bien escrito.
    """

    text = " ".join(text.split())

    if not text or not _is_short(text):
        return text

    # Primero lo escrito tal cual (gentilicio o país); solo después se corrigen
    # erratas, para que "Colombia" no se convierta en "Colombiano".
    return (
        _exact(text, _DEMONYM_FORMS)
        or _exact(text, _COUNTRY_FORMS)
        or _fuzzy(text, _DEMONYM_FORMS)
        or _fuzzy(text, _COUNTRY_FORMS)
        or _title(text)
    )


def nationality_group(text: str) -> str:
    """Etiqueta común para contar en estadísticas: "colombiana", "Colombiano" y "Colombia" -> "Colombiano/a"."""

    text = " ".join(text.split())

    if not text or not _is_short(text):
        return text

    key = _fold(text)

    if key in _NATIONALITY_GROUP:
        return _NATIONALITY_GROUP[key]

    close = difflib.get_close_matches(key, list(_NATIONALITY_GROUP), n=1, cutoff=FUZZY_CUTOFF)

    return _NATIONALITY_GROUP[close[0]] if close else _title(text)


def group_for_stats(field: str, value: str) -> str:
    """Unifica variantes de escritura de un mismo dato al contarlo en las estadísticas."""

    if field == "current_country":
        return normalize_country(value)

    if field == "nationality":
        return nationality_group(value)

    return value
