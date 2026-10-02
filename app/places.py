"""Swiss places for the search setup: a home town + a commute radius -> the location words a
posting's location must contain (LOCATION_KEYWORDS), the cantons to search (WHERE, Job-Room).

Coordinates are approximate town centres (enough for a commute radius). Each place lists the
spellings job boards use (Genève / Geneva / Genf / Ginevra...).
"""
import math
import unicodedata

CANTONS = {   # code -> (names used by job boards; the first is the local name)
    "GE": ["Genève", "geneva", "genf", "ginevra", "canton de genève"],
    "VD": ["Vaud", "waadt", "canton de vaud"],
    "FR": ["Fribourg", "freiburg", "friburgo"],
    "NE": ["Neuchâtel", "neuchatel", "neuenburg"],
    "VS": ["Valais", "wallis", "vallese"],
    "JU": ["Jura"],
    "BE": ["Bern", "berne", "berna"],
    "SO": ["Solothurn", "soleure", "soletta"],
    "BS": ["Basel-Stadt", "basel", "bâle", "basilea"],
    "BL": ["Basel-Landschaft", "baselland", "bâle-campagne"],
    "AG": ["Aargau", "argovie", "argovia"],
    "ZH": ["Zürich", "zurich", "zurigo"],
    "ZG": ["Zug", "zoug", "zugo"],
    "LU": ["Luzern", "lucerne", "lucerna"],
    "SZ": ["Schwyz"],
    "NW": ["Nidwalden"], "OW": ["Obwalden"], "UR": ["Uri"], "GL": ["Glarus"],
    "SG": ["St. Gallen", "st gallen", "saint-gall", "san gallo"],
    "TG": ["Thurgau", "thurgovie", "turgovia"],
    "SH": ["Schaffhausen", "schaffhouse", "sciaffusa"],
    "AR": ["Appenzell Ausserrhoden"], "AI": ["Appenzell Innerrhoden"],
    "GR": ["Graubünden", "grisons", "grigioni"],
    "TI": ["Ticino", "tessin"],
}
ROMANDIE = {"GE", "VD", "FR", "NE", "VS", "JU"}
REGION_WORDS = {"romandie": ["romandie", "suisse romande", "lake geneva", "arc lémanique"],
                "ticino": ["svizzera italiana"], "de": ["deutschschweiz"]}

# (spellings, lat, lon, canton)
PLACES = [
    (["Genève", "geneva", "genf", "ginevra", "geneve"], 46.204, 6.143, "GE"),
    (["Carouge"], 46.181, 6.139, "GE"), (["Lancy"], 46.189, 6.114, "GE"), (["Vernier"], 46.217, 6.085, "GE"),
    (["Meyrin"], 46.234, 6.080, "GE"), (["Onex"], 46.184, 6.101, "GE"), (["Thônex", "thonex"], 46.194, 6.199, "GE"),
    (["Plan-les-Ouates"], 46.168, 6.117, "GE"), (["Satigny"], 46.214, 6.037, "GE"), (["Versoix"], 46.284, 6.163, "GE"),
    (["Chêne-Bourg", "chene-bourg"], 46.196, 6.195, "GE"), (["Grand-Saconnex", "le grand-saconnex"], 46.232, 6.121, "GE"),
    (["Lausanne"], 46.520, 6.633, "VD"), (["Renens"], 46.539, 6.588, "VD"), (["Prilly"], 46.536, 6.604, "VD"),
    (["Pully"], 46.510, 6.662, "VD"), (["Ecublens", "écublens"], 46.528, 6.561, "VD"), (["Crissier"], 46.546, 6.576, "VD"),
    (["Bussigny"], 46.551, 6.552, "VD"), (["Morges"], 46.511, 6.498, "VD"), (["Nyon"], 46.383, 6.239, "VD"),
    (["Gland"], 46.421, 6.270, "VD"), (["Rolle"], 46.459, 6.337, "VD"), (["Vevey"], 46.460, 6.843, "VD"),
    (["Montreux"], 46.433, 6.911, "VD"), (["La Tour-de-Peilz"], 46.453, 6.858, "VD"),
    (["Yverdon-les-Bains", "yverdon*"], 46.778, 6.641, "VD"), (["Epalinges"], 46.549, 6.668, "VD"),
    (["Le Mont-sur-Lausanne"], 46.558, 6.631, "VD"), (["Echallens"], 46.642, 6.633, "VD"), (["Moudon"], 46.668, 6.798, "VD"),
    (["Aigle"], 46.318, 6.970, "VD"), (["Villeneuve"], 46.398, 6.928, "VD"), (["Saint-Sulpice", "st-sulpice"], 46.510, 6.560, "VD"),
    (["Payerne"], 46.822, 6.938, "VD"), (["Coppet"], 46.316, 6.191, "VD"), (["Aubonne"], 46.495, 6.391, "VD"),
    (["Cossonay"], 46.614, 6.507, "VD"), (["Lutry"], 46.503, 6.686, "VD"), (["Orbe"], 46.725, 6.532, "VD"),
    (["Bex"], 46.250, 7.010, "VD"), (["Chavannes-près-Renens"], 46.530, 6.571, "VD"), (["Etoy"], 46.486, 6.418, "VD"),
    (["Allaman"], 46.470, 6.400, "VD"), (["Préverenges"], 46.517, 6.527, "VD"),
    (["Fribourg", "freiburg", "friburgo"], 46.806, 7.161, "FR"), (["Bulle"], 46.619, 7.057, "FR"),
    (["Villars-sur-Glâne"], 46.790, 7.120, "FR"), (["Morat", "murten"], 46.928, 7.117, "FR"),
    (["Estavayer*"], 46.849, 6.846, "FR"), (["Romont"], 46.697, 6.918, "FR"), (["Châtel-Saint-Denis", "châtel-st-denis"], 46.527, 6.901, "FR"),
    (["Neuchâtel", "neuchatel", "neuenburg"], 46.990, 6.931, "NE"), (["La Chaux-de-Fonds"], 47.100, 6.826, "NE"),
    (["Le Locle"], 47.057, 6.749, "NE"), (["Marin-Epagnier", "marin"], 47.010, 6.999, "NE"),
    (["Sion", "sitten"], 46.233, 7.360, "VS"), (["Sierre", "siders"], 46.292, 7.535, "VS"), (["Martigny"], 46.102, 7.072, "VS"),
    (["Monthey"], 46.255, 6.954, "VS"), (["Visp", "viège"], 46.294, 7.881, "VS"), (["Brig", "brigue"], 46.316, 7.988, "VS"),
    (["Conthey"], 46.210, 7.300, "VS"), (["Saint-Maurice"], 46.216, 7.003, "VS"),
    (["Delémont", "delemont", "delsberg"], 47.365, 7.343, "JU"), (["Porrentruy"], 47.416, 7.075, "JU"),
    (["Bern", "berne", "berna"], 46.948, 7.447, "BE"), (["Biel", "bienne", "biel/bienne"], 47.137, 7.247, "BE"),
    (["Thun", "thoune"], 46.758, 7.628, "BE"), (["Köniz", "koniz"], 46.924, 7.415, "BE"), (["Burgdorf"], 47.059, 7.628, "BE"),
    (["Langenthal"], 47.215, 7.786, "BE"), (["Ittigen"], 46.975, 7.482, "BE"), (["Ostermundigen"], 46.956, 7.487, "BE"),
    (["Muri bei Bern"], 46.931, 7.487, "BE"), (["Interlaken"], 46.686, 7.863, "BE"),
    (["Solothurn", "soleure"], 47.208, 7.537, "SO"), (["Olten"], 47.350, 7.903, "SO"), (["Grenchen", "granges"], 47.192, 7.396, "SO"),
    (["Basel", "bâle", "bale", "basilea"], 47.560, 7.588, "BS"), (["Riehen"], 47.579, 7.648, "BS"),
    (["Allschwil"], 47.551, 7.536, "BL"), (["Muttenz"], 47.523, 7.645, "BL"), (["Pratteln"], 47.521, 7.694, "BL"),
    (["Liestal"], 47.484, 7.735, "BL"), (["Reinach"], 47.494, 7.591, "BL"), (["Binningen"], 47.541, 7.569, "BL"),
    (["Münchenstein"], 47.518, 7.618, "BL"), (["Kaiseraugst"], 47.540, 7.725, "AG"),
    (["Aarau"], 47.393, 8.044, "AG"), (["Baden"], 47.473, 8.307, "AG"), (["Wettingen"], 47.466, 8.316, "AG"),
    (["Brugg"], 47.481, 8.208, "AG"), (["Lenzburg"], 47.388, 8.180, "AG"), (["Zofingen"], 47.288, 7.946, "AG"),
    (["Wohlen"], 47.352, 8.278, "AG"), (["Rheinfelden"], 47.554, 7.794, "AG"), (["Spreitenbach"], 47.420, 8.366, "AG"),
    (["Zürich", "zurich", "zurigo", "zuerich"], 47.377, 8.540, "ZH"), (["Winterthur", "winterthour"], 47.500, 8.724, "ZH"),
    (["Uster"], 47.348, 8.718, "ZH"), (["Dübendorf", "dubendorf"], 47.397, 8.618, "ZH"), (["Wallisellen"], 47.415, 8.596, "ZH"),
    (["Opfikon", "glattbrugg"], 47.431, 8.572, "ZH"), (["Kloten"], 47.451, 8.585, "ZH"), (["Schlieren"], 47.396, 8.447, "ZH"),
    (["Dietikon"], 47.404, 8.400, "ZH"), (["Adliswil"], 47.310, 8.525, "ZH"), (["Thalwil"], 47.295, 8.564, "ZH"),
    (["Horgen"], 47.260, 8.598, "ZH"), (["Wädenswil"], 47.230, 8.672, "ZH"), (["Meilen"], 47.270, 8.643, "ZH"),
    (["Küsnacht"], 47.318, 8.584, "ZH"), (["Bülach"], 47.522, 8.540, "ZH"), (["Regensdorf"], 47.434, 8.469, "ZH"),
    (["Rüschlikon"], 47.307, 8.557, "ZH"), (["Wetzikon"], 47.326, 8.797, "ZH"), (["Volketswil"], 47.390, 8.690, "ZH"),
    (["Zug", "zoug"], 47.166, 8.516, "ZG"), (["Baar"], 47.196, 8.528, "ZG"), (["Cham"], 47.182, 8.463, "ZG"),
    (["Rotkreuz", "risch"], 47.141, 8.431, "ZG"), (["Steinhausen"], 47.195, 8.486, "ZG"),
    (["Luzern", "lucerne", "lucerna"], 47.050, 8.309, "LU"), (["Kriens"], 47.033, 8.279, "LU"), (["Emmen"], 47.080, 8.300, "LU"),
    (["Ebikon"], 47.080, 8.340, "LU"), (["Root"], 47.110, 8.390, "LU"), (["Sursee"], 47.171, 8.111, "LU"),
    (["Schwyz"], 47.021, 8.653, "SZ"), (["Pfäffikon"], 47.201, 8.778, "SZ"), (["Freienbach"], 47.205, 8.758, "SZ"),
    (["Lachen"], 47.192, 8.854, "SZ"),
    (["St. Gallen", "st gallen", "st.gallen", "saint-gall", "san gallo"], 47.424, 9.377, "SG"), (["Wil"], 47.462, 9.045, "SG"),
    (["Rapperswil*", "jona"], 47.227, 8.818, "SG"), (["Gossau"], 47.415, 9.255, "SG"), (["Buchs"], 47.165, 9.478, "SG"),
    (["Frauenfeld"], 47.557, 8.899, "TG"), (["Kreuzlingen"], 47.650, 9.175, "TG"), (["Arbon"], 47.516, 9.431, "TG"),
    (["Weinfelden"], 47.566, 9.107, "TG"), (["Schaffhausen", "schaffhouse"], 47.696, 8.635, "SH"),
    (["Chur", "coire", "coira"], 46.850, 9.532, "GR"), (["Davos"], 46.802, 9.836, "GR"), (["St. Moritz", "st moritz"], 46.498, 9.839, "GR"),
    (["Lugano"], 46.004, 8.951, "TI"), (["Bellinzona"], 46.195, 9.024, "TI"), (["Locarno"], 46.170, 8.795, "TI"),
    (["Mendrisio"], 45.870, 8.981, "TI"), (["Chiasso"], 45.832, 9.031, "TI"), (["Manno"], 46.030, 8.920, "TI"),
    (["Glarus"], 47.040, 9.068, "GL"), (["Appenzell"], 47.331, 9.409, "AI"), (["Herisau"], 47.386, 9.279, "AR"),
    (["Stans"], 46.958, 8.366, "NW"), (["Sarnen"], 46.896, 8.246, "OW"), (["Altdorf"], 46.881, 8.644, "UR"),
]
COUNTRY_WORDS = ["switzerland", "suisse", "schweiz", "svizzera"]


def _fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def find(name):
    """The place for a town name (any listed spelling, accents ignored), or None."""
    key = _fold(name).rstrip("*")
    if not key:
        return None
    for p in PLACES:
        if any(_fold(s).rstrip("*") == key for s in p[0]):
            return p
    for p in PLACES:                      # "Lausanne VD", "Geneva, Switzerland"
        if any(_fold(s).rstrip("*") and _fold(s).rstrip("*") in key.replace(",", " ").split() for s in p[0]):
            return p
    return None


def town_names():
    return sorted(p[0][0] for p in PLACES)


def _km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[2], b[1], b[2]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def around(home, radius_km):
    """Places within radius_km of the home town (straight line), nearest first."""
    p = find(home)
    if not p:
        return []
    return sorted((q for q in PLACES if _km(p, q) <= radius_km), key=lambda q: _km(p, q))


def search_area(home, radius_km, whole_country=False):
    """(location_keywords, cantons) for a home town + commute radius."""
    near = around(home, radius_km)
    cantons = []
    for q in near:
        if q[3] not in cantons:
            cantons.append(q[3])
    words = []
    for q in near:
        for s in q[0]:
            w = s.lower()
            if w not in words:
                words.append(w)
    for c in cantons:
        for s in CANTONS[c]:
            if s.lower() not in words:
                words.append(s.lower())
    if cantons and set(cantons) <= ROMANDIE:
        words += [w for w in REGION_WORDS["romandie"] if w not in words]
    if whole_country:
        words += [w for w in COUNTRY_WORDS if w not in words]
    return words, cantons


def canton_names(codes):
    """Local canton names ("Vaud", "Genève") for WHERE / the aggregators."""
    return [CANTONS[c][0] for c in codes if c in CANTONS]
