"""
Generate a realistic ONIX 3.0 seed file with 25 books covering:
  - Genres: literary fiction, crime, SF/fantasy, history, biography,
    cookery, children's, YA, business, self-help, science
  - Formats: paperback, hardback, ebook
  - Publishers: 6 distinct publishers / imprints
  - Rights mix: world, UK-only, UK+IE, Europe
  - Status mix: active, forthcoming, out-of-print
  - Multiple contributors (author + translator / author + editor)
  - BIC, BISAC, and Thema subject codes
  - GBP RRPs throughout; USD on world-rights titles

Run:
    python scripts/generate_seed_onix.py > tests/fixtures/seed_catalog.xml
Then ingest:
    python scripts/seed_db.py
"""
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SeedBook:
    ref: str
    isbn13: str
    title: str
    subtitle: str = ""
    form: str = "BC"           # BC=paperback, BB=hardback, DG=ebook
    form_detail: str = ""
    pages: int = 0
    language: str = "eng"
    pub_date: str = ""
    status: str = "04"         # 04=active
    publisher: str = ""
    imprint: str = ""
    description: str = ""
    toc: str = ""
    cover: str = ""
    audience: str = "01"       # 01=general trade
    edition: int = 0
    contributors: list = field(default_factory=list)  # (role, name, inverted, bio)
    bic: list = field(default_factory=list)            # (code, heading, main)
    bisac: list = field(default_factory=list)          # (code, heading)
    thema: list = field(default_factory=list)          # (code, heading)
    rights: str = "WORLD"      # "WORLD", "GB IE", "EUROPE", "GB"
    rights_type: str = "01"    # 01=exclusive
    rrp_gbp: str = ""
    rrp_usd: str = ""
    notification: str = "03"
    # Physical dimensions in mm (0 = not set)
    height_mm: int = 0
    width_mm: int = 0


BOOKS = [
    # ── Literary fiction ─────────────────────────────────────────────────────
    SeedBook(
        ref="MB-001", isbn13="9781784879999", title="The Weight of Water",
        subtitle="A Novel", form="BC", pages=304, language="eng",
        pub_date="20230601", status="04",
        publisher="Canongate Books", imprint="Canongate",
        description="A hypnotic debut novel set between contemporary Edinburgh and 1960s Jamaica. When archivist Vera Mackenzie opens a water-damaged trunk of letters in the National Library of Scotland, she begins a journey that will upend everything she knows about her family — and herself.",
        cover="https://covers.seed.dev/9781784879999.jpg",
        contributors=[
            ("A01","Amara Osei-Mensah","Osei-Mensah, Amara","Amara Osei-Mensah was born in Accra and raised in Edinburgh. Her short fiction has appeared in Granta and The White Review."),
        ],
        bic=[("FA","Modern & contemporary fiction",True)],
        bisac=[("FIC019000","FICTION / Literary",False)],
        thema=[("FBA","Literary fiction",False)],
        rights="WORLD", rrp_gbp="9.99", rrp_usd="14.99",
    ),
    SeedBook(
        ref="MB-002", isbn13="9780571383955", title="The Cartographer's Daughter",
        form="BB", pages=384, language="eng",
        pub_date="20240214", status="04",
        publisher="Faber & Faber", imprint="Faber Fiction",
        description="Set in Lisbon at the turn of the twentieth century, this sweeping novel follows the illegitimate daughter of a royal cartographer who inherits his life's work — a map of a country that does not exist. Winner of the Costa Novel Award.",
        cover="https://covers.seed.dev/9780571383955.jpg",
        contributors=[
            ("A01","Inês Carvalho","Carvalho, Inês","Inês Carvalho is a Portuguese novelist and translator. Her work has been translated into twenty-two languages."),
            ("A36","Daniel Shaw","Shaw, Daniel",None),
        ],
        bic=[("FRH","Historical fiction",True),("FA","Modern & contemporary fiction",False)],
        bisac=[("FIC014000","FICTION / Historical / General",False)],
        thema=[("FHH","Historical fiction",True)],
        rights="WORLD", rrp_gbp="18.99", rrp_usd="27.00",
    ),

    # ── Crime / Thriller ─────────────────────────────────────────────────────
    SeedBook(
        ref="MB-003", isbn13="9781529920741", title="Dead Ground",
        subtitle="A DS Nadia Okafor Investigation", form="BC", pages=416,
        pub_date="20230904", status="04",
        publisher="Hodder & Stoughton", imprint="Hodder Paperbacks",
        description="Detective Sergeant Nadia Okafor is called to a moorland crime scene where three bodies have been arranged in an unmistakeable pattern. As the Yorkshire winter closes in, Nadia realises the killer is one step ahead — and that the past she has spent a decade burying is about to surface.",
        cover="https://covers.seed.dev/9781529920741.jpg",
        contributors=[("A01","Pete Rawlings","Rawlings, Pete","Pete Rawlings is a former detective constable turned crime writer. He lives in West Yorkshire.")],
        bic=[("FF","Crime, thriller & adventure",True),("FHD","Crime & mystery",False)],
        bisac=[("FIC022000","FICTION / Mystery & Detective / General",False)],
        thema=[("FH","Thriller / suspense fiction",True)],
        rights="GB IE", rights_type="01", rrp_gbp="9.99",
    ),
    SeedBook(
        ref="MB-004", isbn13="9780241624708", title="The Honest Thief",
        form="BB", pages=336, pub_date="20240118", status="04",
        publisher="Michael Joseph", imprint="Michael Joseph",
        description="A retired Interpol agent. A stolen Vermeer. And a confession that arrives forty years too late. John le Carré meets Patricia Highsmith in this taut, elegant thriller set across Amsterdam, Geneva and the Amalfi Coast.",
        cover="https://covers.seed.dev/9780241624708.jpg",
        contributors=[("A01","Margot Heiselberg","Heiselberg, Margot","Margot Heiselberg is the author of six internationally bestselling thrillers. She divides her time between Hamburg and Tuscany.")],
        bic=[("FF","Crime, thriller & adventure",True)],
        bisac=[("FIC031000","FICTION / Thrillers / General",False)],
        thema=[("FH","Thriller / suspense fiction",True)],
        rights="WORLD", rrp_gbp="20.00", rrp_usd="29.00",
    ),

    # ── Science Fiction / Fantasy ─────────────────────────────────────────────
    SeedBook(
        ref="MB-005", isbn13="9780575135215", title="The Silence Engine",
        form="BC", pages=512, pub_date="20230327", status="04",
        publisher="Gollancz", imprint="Gollancz",
        description="Far-future Earth. The last engineers of a dying civilisation have built a machine designed to delete language itself — a weapon that makes thought impossible. A linguist, a soldier, and an AI must cross a continent where silence has already fallen to destroy it. A breathtaking debut that asks what it means to be human when the words run out.",
        cover="https://covers.seed.dev/9780575135215.jpg",
        contributors=[("A01","Kenji Watanabe-Fox","Watanabe-Fox, Kenji","Kenji Watanabe-Fox holds a PhD in computational linguistics and writes speculative fiction in his spare time. The Silence Engine is his first novel.")],
        bic=[("FLS","Science fiction",True)],
        bisac=[("FIC028000","FICTION / Science Fiction / General",False)],
        thema=[("FYT","Science fiction",True)],
        rights="WORLD", rrp_gbp="9.99", rrp_usd="15.99",
    ),
    SeedBook(
        ref="MB-006", isbn13="9781473233591", title="The Glass Parliament",
        subtitle="The Sunken Throne Book One", form="BB", pages=624,
        pub_date="20240307", status="04",
        publisher="Hodder & Stoughton", imprint="Hodder Fantasy",
        description="In a world where the dead vote and memory is currency, a disgraced senator discovers that someone is stealing the votes of the recently deceased. Epic secondary-world fantasy for readers of Ursula Le Guin and N.K. Jemisin.",
        cover="https://covers.seed.dev/9781473233591.jpg",
        contributors=[("A01","Céleste Renard","Renard, Céleste","Céleste Renard is a French novelist and screenwriter based in Paris and Montreal. She is the author of the Golem Quartet.")],
        bic=[("FM","Fantasy",True)],
        bisac=[("FIC009000","FICTION / Fantasy / General",False)],
        thema=[("FFC","Fantasy",True)],
        rights="GB IE", rights_type="01", rrp_gbp="22.00",
    ),

    # ── History & Biography ───────────────────────────────────────────────────
    SeedBook(
        ref="MB-007", isbn13="9780241515938", title="The Longitude Merchants",
        subtitle="How Britain's Clockmakers Won the Race to Map the World",
        form="BB", pages=368, pub_date="20230518", status="04",
        publisher="Allen Lane", imprint="Allen Lane",
        description="The gripping history of the Longitude Act of 1714, the clockmakers who competed for its prize, and the sea captains whose lives depended on the winner. A vivid account of science, empire, and obsession.",
        cover="https://covers.seed.dev/9780241515938.jpg",
        contributors=[("A01","Dr Helena Marsh","Marsh, Helena","Dr Helena Marsh is a historian of science at the University of Oxford. She has written for the TLS and the London Review of Books.")],
        bic=[("HBJD","British history",True),("WN","Popular science",False)],
        bisac=[("HIS015000","HISTORY / Europe / Great Britain",False)],
        thema=[("NHB","World history",True)],
        rights="WORLD", rrp_gbp="25.00", rrp_usd="35.00",
    ),
    SeedBook(
        ref="MB-008", isbn13="9780008509743", title="First Light",
        subtitle="The Life of Sir William Herschel",
        form="BC", pages=464, pub_date="20231102", status="04",
        publisher="HarperCollins", imprint="William Collins",
        description="A magnificent biography of the musician-turned-astronomer who discovered Uranus, built the largest telescope on Earth, and catalogued the night sky with his sister Caroline by his side. Based on newly uncovered correspondence from the Royal Astronomical Society.",
        cover="https://covers.seed.dev/9780008509743.jpg",
        contributors=[("A01","Saul Ingram","Ingram, Saul","Saul Ingram is the author of several acclaimed biographies of scientists and explorers. He was awarded the PEN Hessell-Tiltman Prize in 2021.")],
        bic=[("BGH","Biography: science, technology & medicine",True)],
        bisac=[("BIO015000","BIOGRAPHY & AUTOBIOGRAPHY / Science & Technology",False)],
        thema=[("DNB","Biography",True)],
        rights="WORLD", rrp_gbp="12.99", rrp_usd="18.99",
    ),

    # ── Cookery ───────────────────────────────────────────────────────────────
    SeedBook(
        ref="MB-009", isbn13="9781787138162", title="Salt, Fat, Sunday",
        subtitle="British Home Cooking Reinvented",
        form="BB", pages=288, pub_date="20230907", status="04",
        publisher="Quadrille", imprint="Quadrille",
        description="Sixty recipes that take Sunday lunch seriously again. Built around the doctrine that good fat, good salt, and good time are the only three things a good cook needs. From slow-braised ox cheek to the definitive bread sauce, this is proper British cooking for a new generation.",
        cover="https://covers.seed.dev/9781787138162.jpg",
        contributors=[("A01","Tom Birch","Birch, Tom","Tom Birch is a chef and restaurateur. His restaurant The Granary in Ludlow has held a Michelin star since 2019.")],
        bic=[("WBB","Cooking with specific ingredients",True),("WBX","National & regional cuisine",False)],
        bisac=[("CKB000000","COOKING / General",False)],
        thema=[("WBX","Cooking with specific ingredients",True)],
        rights="WORLD", rrp_gbp="28.00", rrp_usd="40.00",
    ),
    SeedBook(
        ref="MB-010", isbn13="9781529388718", title="Small Plates",
        subtitle="A Plant-Based Cookbook for Every Season",
        form="BC", pages=256, pub_date="20240201", status="04",
        publisher="Ebury Press", imprint="Ebury Press",
        description="Over 80 vegetarian and vegan recipes organised by season — from spring pea and ricotta bruschetta to a roasted root tray bake that has become legendary at the author's Edinburgh supper club.",
        cover="https://covers.seed.dev/9781529388718.jpg",
        contributors=[("A01","Anya Kovalenko","Kovalenko, Anya","Anya Kovalenko is a Ukrainian-Scottish cook and food stylist. She runs the Almanac supper club in Edinburgh.")],
        bic=[("WBJ","Vegetarian cookery",True)],
        bisac=[("CKB050000","COOKING / Vegetarian & Vegan",False)],
        thema=[("WBVV","Vegetarian cooking",True)],
        rights="WORLD", rrp_gbp="22.00", rrp_usd="32.00",
    ),

    # ── Children's ────────────────────────────────────────────────────────────
    SeedBook(
        ref="MB-011", isbn13="9780192779809", title="The Clockwork Fox",
        form="BC", pages=192, pub_date="20230901", status="04",
        publisher="Oxford University Press", imprint="OUP Children's",
        description="Ten-year-old Mira discovers a small brass fox in her grandmother's attic. When it blinks at her, she realizes this is no ordinary toy — and that the world beneath the city streets is far stranger than she ever imagined. First in the Clockwork Tales series.",
        cover="https://covers.seed.dev/9780192779809.jpg",
        contributors=[("A01","Ruth Holloway","Holloway, Ruth","Ruth Holloway is the author of the Luna Fox series and the Starwatch trilogy. She lives in Bath with too many cats.")],
        bic=[("YFB","Children's / teenage fiction: general",True)],
        bisac=[("JUV037000","JUVENILE FICTION / Fantasy & Magic",False)],
        thema=[("YFH","Children's / teenage fantasy",True)],
        audience="02",  # children
        rights="WORLD", rrp_gbp="7.99", rrp_usd="10.99",
    ),
    SeedBook(
        ref="MB-012", isbn13="9781406392241", title="This Side of Midnight",
        subtitle="A Story of Bravery and Stars",
        form="BC", pages=352, pub_date="20240404", status="04",
        publisher="Walker Books", imprint="Walker Books",
        description="Fifteen-year-old Sol has always kept her head down. But when her school is threatened with closure, she has to stand up — and discovers the power of her own voice. A warm, urgent YA novel about class, community and the courage it takes to speak.",
        cover="https://covers.seed.dev/9781406392241.jpg",
        contributors=[("A01","Marcus Adesanya","Adesanya, Marcus","Marcus Adesanya grew up in Peckham and now lives in Hackney. He works as a secondary school teacher.")],
        bic=[("YFB","Children's / teenage fiction: general",True)],
        bisac=[("YAF019000","YOUNG ADULT FICTION / General",False)],
        thema=[("YFB","Young adult fiction",True)],
        audience="03",  # YA
        rights="WORLD", rrp_gbp="8.99", rrp_usd="12.99",
    ),

    # ── Business & self-help ──────────────────────────────────────────────────
    SeedBook(
        ref="MB-013", isbn13="9781847943255", title="The Depth Trap",
        subtitle="Why Shallow Work Is Killing Your Best Thinking",
        form="BC", pages=288, pub_date="20230504", status="04",
        publisher="Profile Books", imprint="Profile Business",
        description="In an era of constant notification, the ability to think deeply is becoming rare — and therefore increasingly valuable. Combining cognitive science with practical strategy, The Depth Trap is a guide to reclaiming the focused time your best work demands.",
        cover="https://covers.seed.dev/9781847943255.jpg",
        contributors=[("A01","Dr Priya Banerjee","Banerjee, Priya","Dr Priya Banerjee is a cognitive scientist at University College London. Her research on attention and deep work has been cited in The Economist and Wired.")],
        bic=[("KJ","Business & management",True),("VSP","Personal development",False)],
        bisac=[("BUS042000","BUSINESS & ECONOMICS / Management",False)],
        thema=[("KJ","Business",True)],
        rights="WORLD", rrp_gbp="14.99", rrp_usd="20.00",
    ),
    SeedBook(
        ref="MB-014", isbn13="9780349127903", title="Honest Numbers",
        subtitle="A Non-Maths Guide to Data That Matters",
        form="BC", pages=240, pub_date="20240115", status="04",
        publisher="Little, Brown Book Group", imprint="Sphere",
        description="Charts, figures, and statistics are everywhere — and most of them are misleading. This practical handbook teaches you to read data honestly, spot manipulation, and use numbers to make better decisions without needing a maths degree.",
        contributors=[("A01","Oliver Grant","Grant, Oliver","Oliver Grant is a data journalist at the Financial Times.")],
        bic=[("KJQ","Business mathematics & systems",True)],
        bisac=[("BUS061000","BUSINESS & ECONOMICS / Statistics",False)],
        thema=[("KN","Business mathematics",True)],
        rights="WORLD", rrp_gbp="12.99", rrp_usd="18.00",
    ),

    # ── Popular science ───────────────────────────────────────────────────────
    SeedBook(
        ref="MB-015", isbn13="9780241618638", title="The Gut Feeling",
        subtitle="The New Science of Your Second Brain",
        form="BC", pages=320, pub_date="20230213", status="04",
        publisher="Penguin Random House UK", imprint="Viking",
        description="Your gut contains 500 million neurons, communicates with your brain constantly, and may be influencing your mood, your decisions, and your mental health in ways science is only beginning to understand. A revelatory, accessible account of the microbiome revolution.",
        cover="https://covers.seed.dev/9780241618638.jpg",
        contributors=[("A01","Professor Leena Harjula","Harjula, Leena","Professor Leena Harjula holds the Chair in Microbiome Research at King's College London. Her TED talk has been viewed 12 million times.")],
        bic=[("MJ","Medical science",True),("WN","Popular science",False)],
        bisac=[("SCI000000","SCIENCE / General",False)],
        thema=[("MBP","Popular science",True)],
        rights="WORLD", rrp_gbp="10.99", rrp_usd="16.99",
    ),
    SeedBook(
        ref="MB-016", isbn13="9780008500153", title="Dark Matter, Bright Minds",
        subtitle="The Search for What the Universe Is Made Of",
        form="BC", pages=352, pub_date="20231116", status="04",
        publisher="HarperCollins", imprint="HarperCollins Science",
        description="Ninety-five per cent of the universe is invisible. In this thrilling account of one of science's greatest unsolved mysteries, physicist Yusuf Al-Rashid takes us behind the scenes of the experiments, rivalries and eureka moments in the search for dark matter and dark energy.",
        contributors=[("A01","Dr Yusuf Al-Rashid","Al-Rashid, Yusuf","Dr Yusuf Al-Rashid is a particle physicist at CERN and a regular contributor to New Scientist.")],
        bic=[("PHD","Cosmology & the universe",True)],
        bisac=[("SCI004000","SCIENCE / Astronomy",False)],
        thema=[("PHD","Cosmology",True)],
        rights="WORLD", rrp_gbp="10.99", rrp_usd="16.99",
    ),

    # ── Politics & current affairs ────────────────────────────────────────────
    SeedBook(
        ref="MB-017", isbn13="9780241543788", title="The Trust Gap",
        subtitle="How Institutions Lost the Public — and How They Can Win It Back",
        form="BB", pages=288, pub_date="20240320", status="04",
        publisher="Penguin Random House UK", imprint="Allen Lane",
        description="From parliaments to hospitals to the press, trust in institutions is at its lowest level in recorded history. Drawing on decades of polling data and interviews with politicians, chief executives and activists, this is a clear-eyed diagnosis — and a credible prescription.",
        contributors=[("A01","Fatima Iqbal","Iqbal, Fatima","Fatima Iqbal is a political scientist at the London School of Economics and a columnist for the Guardian.")],
        bic=[("JP","Politics & government",True)],
        bisac=[("POL000000","POLITICAL SCIENCE / General",False)],
        thema=[("JP","Politics",True)],
        rights="WORLD", rrp_gbp="22.00", rrp_usd="30.00",
    ),

    # ── Memoir ────────────────────────────────────────────────────────────────
    SeedBook(
        ref="MB-018", isbn13="9780008513054", title="The River Home",
        subtitle="A Memoir of Water, Memory and Return",
        form="BC", pages=272, pub_date="20230706", status="04",
        publisher="HarperCollins", imprint="Fourth Estate",
        description="After his father's death, the author canoes the length of the River Severn, retracing the journeys they took together when he was a boy. Part elegy, part nature writing, part family history — a book about the landscapes we carry inside us.",
        cover="https://covers.seed.dev/9780008513054.jpg",
        contributors=[("A01","James Whitmore","Whitmore, James","James Whitmore is a journalist, broadcaster and the author of two previous books. He lives in Shropshire.")],
        bic=[("BM","Memoirs",True),("WN","Popular science",False)],
        bisac=[("BIO026000","BIOGRAPHY & AUTOBIOGRAPHY / Personal Memoirs",False)],
        thema=[("DN","Biography",True)],
        rights="WORLD", rrp_gbp="9.99", rrp_usd="15.99",
    ),

    # ── Health & wellbeing ────────────────────────────────────────────────────
    SeedBook(
        ref="MB-019", isbn13="9781780725789", title="Rest Is Resistance",
        subtitle="Reclaiming Your Right to Do Nothing",
        form="BC", pages=224, pub_date="20230301", status="04",
        publisher="Canongate Books", imprint="Canongate",
        description="In a culture that treats exhaustion as a status symbol, this manifesto argues for rest as a political act. Drawing on philosophy, neuroscience and the author's own experience of burnout, it offers both a critique and a practical path forward.",
        contributors=[("A01","Rosie Tanner","Tanner, Rosie","Rosie Tanner is a writer and activist who has contributed to the Guardian, Vice and gal-dem.")],
        bic=[("VSP","Personal development",True)],
        bisac=[("SEL016000","SELF-HELP / Personal Growth / General",False)],
        thema=[("VX","Self-help",True)],
        rights="WORLD", rrp_gbp="9.99", rrp_usd="14.99",
    ),

    # ── Language & reference ──────────────────────────────────────────────────
    SeedBook(
        ref="MB-020", isbn13="9780199543854", title="The Story of English",
        subtitle="A History in 100 Words",
        form="BC", pages=336, pub_date="20220915", status="04",
        publisher="Oxford University Press", imprint="OUP",
        description="From 'wyrd' to 'selfie', one hundred words trace the full arc of the English language — its Anglo-Saxon roots, Norman conquests, imperial sprawl and digital future. A witty, erudite history that is also a portrait of the culture and people who spoke it.",
        contributors=[
            ("A01","Professor Nora Quinn","Quinn, Nora","Professor Nora Quinn is Professor of Historical Linguistics at Cambridge. She is the author of The Language of Power and The Last Grammarian."),
            ("B06","Dr Paul Serge","Serge, Paul",None),
        ],
        bic=[("CF","Language",True),("CB","Language: reference & general",False)],
        bisac=[("LAN009000","LANGUAGE ARTS & DISCIPLINES / Linguistics / General",False)],
        thema=[("CB","Language",True)],
        rights="WORLD", rrp_gbp="10.99", rrp_usd="17.99",
    ),

    # ── E-book only ───────────────────────────────────────────────────────────
    SeedBook(
        ref="MB-021", isbn13="9781529394245", title="Pattern Recognition",
        subtitle="How to Think Clearly in a Noisy World",
        form="DG", form_detail="E101",
        pub_date="20240501", status="02",  # forthcoming
        publisher="Hodder & Stoughton", imprint="Hodder Digital",
        description="A former intelligence analyst explains the frameworks she used to separate signal from noise in high-stakes environments — and how the same techniques can transform decision-making in business and daily life. Available as ebook only.",
        contributors=[("A01","Sarah Cullen","Cullen, Sarah","Sarah Cullen spent twelve years as an intelligence analyst before becoming a writer and consultant.")],
        bic=[("VSP","Personal development",True),("KJ","Business",False)],
        bisac=[("SEL010000","SELF-HELP / General",False)],
        thema=[("VS","Self-help",True)],
        rights="WORLD", rrp_gbp="7.99", rrp_usd="9.99",
    ),

    # ── Forthcoming hardback ──────────────────────────────────────────────────
    SeedBook(
        ref="MB-022", isbn13="9780571384892", title="The Sea Librarian",
        form="BB", pages=416, pub_date="20241015", status="02",  # forthcoming
        publisher="Faber & Faber", imprint="Faber Fiction",
        description="When the world's libraries begin sinking into the sea, a network of archivists builds a fleet of floating reading rooms. A novel about books, memory, and what survives the flood.",
        contributors=[("A01","Clara Venn","Venn, Clara","Clara Venn is the author of the prize-winning novel The August Letters. She lives in Cornwall.")],
        bic=[("FA","Modern & contemporary fiction",True)],
        bisac=[("FIC019000","FICTION / Literary",False)],
        thema=[("FBA","Literary fiction",True)],
        rights="GB IE", rights_type="01", rrp_gbp="20.00",
    ),

    # ── Classic reissue ───────────────────────────────────────────────────────
    SeedBook(
        ref="MB-023", isbn13="9780099590286", title="London Fields",
        form="BC", pages=480, pub_date="20201001", status="04",
        publisher="Penguin Random House UK", imprint="Vintage",
        description="Martin Amis's savage, brilliant black comedy about love, games, and the end of everything. A murder mystery told backwards, set in a seedy corner of late-twentieth-century London, where barmaid Nicola Six knows she is going to be killed.",
        contributors=[("A01","Martin Amis","Amis, Martin","Martin Amis (1949–2023) was one of the most celebrated British novelists of his generation.")],
        bic=[("FA","Modern & contemporary fiction",True)],
        bisac=[("FIC019000","FICTION / Literary",False)],
        thema=[("FBA","Literary fiction",True)],
        edition=1,
        rights="WORLD", rrp_gbp="9.99", rrp_usd="16.00",
    ),

    # ── Out of print ─────────────────────────────────────────────────────────
    SeedBook(
        ref="MB-024", isbn13="9780330303675", title="The Wasp Factory",
        form="BC", pages=160, pub_date="19840101", status="06",  # out of print
        publisher="Pan Macmillan", imprint="Pan",
        description="Iain Banks's extraordinary debut. On a small Scottish island, sixteen-year-old Frank Cauldhame performs rituals to hold his world in order, while his brother escapes from a psychiatric hospital. Disturbing, darkly comic, unforgettable. (This edition out of print — see current Abacus edition.)",
        contributors=[("A01","Iain Banks","Banks, Iain","Iain Banks (1954–2013) was a Scottish author of mainstream literary fiction and, as Iain M. Banks, science fiction.")],
        bic=[("FA","Modern & contemporary fiction",True)],
        bisac=[("FIC019000","FICTION / Literary",False)],
        thema=[("FBA","Literary fiction",True)],
        rights="WORLD", rrp_gbp="8.99",
        notification="03",
    ),

    # ── Two publishers sharing a name (tests publisher upsert) ───────────────
    SeedBook(
        ref="MB-025", isbn13="9781399718547", title="The Iron Season",
        subtitle="A Novel of the Raj",
        form="BC", pages=432, pub_date="20231205", status="04",
        publisher="Hodder & Stoughton", imprint="Sceptre",
        description="Delhi, 1919. Three weeks after the Amritsar massacre, a young Indian civil servant must decide whether to risk everything to expose the truth — or keep his silence and survive. A novel about complicity, courage, and the cost of empire.",
        contributors=[
            ("A01","Sunita Chatterjee","Chatterjee, Sunita","Sunita Chatterjee is a British-Indian historian and novelist. She is a Fellow of the Royal Society of Literature."),
        ],
        bic=[("FRH","Historical fiction",True),("FA","Modern & contemporary fiction",False)],
        bisac=[("FIC014000","FICTION / Historical / General",False)],
        thema=[("FHH","Historical fiction",True)],
        rights="WORLD", rrp_gbp="9.99", rrp_usd="14.99",
    ),
]


# ─── XML builder ─────────────────────────────────────────────────────────────

def t(parent, tag, text):
    el = ET.SubElement(parent, tag)
    el.text = str(text)
    return el


def build_onix(books: list[SeedBook]) -> ET.Element:
    root = ET.Element("ONIXMessage")
    root.set("release", "3.0")
    root.set("xmlns", "http://ns.editeur.org/onix/3.0/reference")

    hdr = ET.SubElement(root, "Header")
    sender = ET.SubElement(hdr, "Sender")
    t(sender, "SenderName", "Metabookly Seed Data Generator")
    t(hdr, "SentDateTime", "20260317T000000")
    t(hdr, "MessageNote", "Seed catalog for development — not a real ONIX feed")

    for b in books:
        p = ET.SubElement(root, "Product")
        t(p, "RecordReference", b.ref)
        t(p, "NotificationType", b.notification)

        # Identifiers
        pid = ET.SubElement(p, "ProductIdentifier")
        t(pid, "ProductIDType", "15")
        t(pid, "IDValue", b.isbn13)

        # DescriptiveDetail
        dd = ET.SubElement(p, "DescriptiveDetail")
        t(dd, "ProductComposition", "00")
        t(dd, "ProductForm", b.form)
        if b.form_detail:
            t(dd, "ProductFormDetail", b.form_detail)

        td = ET.SubElement(dd, "TitleDetail")
        t(td, "TitleType", "01")
        te = ET.SubElement(td, "TitleElement")
        t(te, "TitleElementLevel", "01")
        t(te, "TitleText", b.title)
        if b.subtitle:
            t(te, "Subtitle", b.subtitle)

        for idx, (role, name, inverted, bio) in enumerate(b.contributors, 1):
            c = ET.SubElement(dd, "Contributor")
            t(c, "SequenceNumber", str(idx))
            t(c, "ContributorRole", role)
            t(c, "PersonName", name)
            t(c, "PersonNameInverted", inverted)
            parts = inverted.split(", ", 1)
            t(c, "KeyNames", parts[0])
            if len(parts) > 1:
                t(c, "NamesBeforeKey", parts[1])
            if bio:
                t(c, "BiographicalNote", bio)

        if b.edition:
            t(dd, "EditionNumber", str(b.edition))

        lang = ET.SubElement(dd, "Language")
        t(lang, "LanguageRole", "01")
        t(lang, "LanguageCode", b.language)

        if b.pages:
            ext = ET.SubElement(dd, "Extent")
            t(ext, "ExtentType", "00")
            t(ext, "ExtentValue", str(b.pages))
            t(ext, "ExtentUnit", "03")

        # Physical dimensions — default by form type if not explicitly set
        h = b.height_mm or (234 if b.form == "BB" else 198 if b.form in ("BC", "BA") else 0)
        w = b.width_mm or (153 if b.form == "BB" else 129 if b.form in ("BC", "BA") else 0)
        if h and w:
            for mtype, mval in (("01", h), ("02", w)):
                m = ET.SubElement(dd, "Measure")
                t(m, "MeasureType", mtype)
                t(m, "Measurement", str(mval))
                t(m, "MeasureUnit", "03")  # mm

        # Subjects
        for i, (code, heading, main) in enumerate(b.bic):
            s = ET.SubElement(dd, "Subject")
            if main:
                ET.SubElement(s, "MainSubject")
            t(s, "SubjectSchemeIdentifier", "12")
            t(s, "SubjectCode", code)
            t(s, "SubjectHeadingText", heading)

        for entry in b.bisac:
            code, heading = entry[0], entry[1]
            s = ET.SubElement(dd, "Subject")
            t(s, "SubjectSchemeIdentifier", "10")
            t(s, "SubjectCode", code)
            t(s, "SubjectHeadingText", heading)

        for entry in b.thema:
            code, heading = entry[0], entry[1]
            s = ET.SubElement(dd, "Subject")
            t(s, "SubjectSchemeIdentifier", "93")
            t(s, "SubjectCode", code)
            t(s, "SubjectHeadingText", heading)

        aud = ET.SubElement(dd, "Audience")
        t(aud, "AudienceCodeType", "01")
        t(aud, "AudienceCodeValue", b.audience)

        # CollateralDetail
        if b.description or b.cover:
            cd = ET.SubElement(p, "CollateralDetail")
            if b.description:
                tc = ET.SubElement(cd, "TextContent")
                t(tc, "TextType", "03")
                t(tc, "ContentAudience", "00")
                txt = ET.SubElement(tc, "Text")
                txt.set("textformat", "06")
                txt.text = b.description
            if b.cover:
                sr = ET.SubElement(cd, "SupportingResource")
                t(sr, "ResourceContentType", "01")
                t(sr, "ContentAudience", "00")
                t(sr, "ResourceMode", "03")
                rv = ET.SubElement(sr, "ResourceVersion")
                t(rv, "ResourceForm", "02")
                rvf = ET.SubElement(rv, "ResourceVersionFeature")
                t(rvf, "ResourceVersionFeatureType", "01")
                t(rvf, "FeatureValue", "600")
                t(rv, "ResourceLink", b.cover)

        # PublishingDetail
        pd_el = ET.SubElement(p, "PublishingDetail")
        if b.imprint:
            imp = ET.SubElement(pd_el, "Imprint")
            t(imp, "ImprintName", b.imprint)
        pub = ET.SubElement(pd_el, "Publisher")
        t(pub, "PublishingRole", "01")
        t(pub, "PublisherName", b.publisher)
        t(pd_el, "PublishingStatus", b.status)
        if b.pub_date:
            pdate = ET.SubElement(pd_el, "PublishingDate")
            t(pdate, "PublishingDateRole", "01")
            t(pdate, "Date", b.pub_date)

        # Sales rights
        sr_el = ET.SubElement(pd_el, "SalesRights")
        t(sr_el, "SalesRightsType", b.rights_type)
        terr = ET.SubElement(sr_el, "Territory")
        if b.rights == "WORLD":
            t(terr, "RegionsIncluded", "WORLD")
        else:
            t(terr, "CountriesIncluded", b.rights)

        # ProductSupply (RRP only — not availability)
        if b.rrp_gbp or b.rrp_usd:
            ps = ET.SubElement(p, "ProductSupply")
            sd = ET.SubElement(ps, "SupplyDetail")
            sup = ET.SubElement(sd, "Supplier")
            t(sup, "SupplierRole", "01")
            t(sup, "SupplierName", b.publisher)
            t(sd, "ProductAvailability", "20")
            if b.rrp_gbp:
                pr = ET.SubElement(sd, "Price")
                t(pr, "PriceType", "02")
                t(pr, "PriceAmount", b.rrp_gbp)
                t(pr, "CurrencyCode", "GBP")
                pr_terr = ET.SubElement(pr, "Territory")
                t(pr_terr, "RegionsIncluded", "WORLD")
            if b.rrp_usd:
                pr = ET.SubElement(sd, "Price")
                t(pr, "PriceType", "02")
                t(pr, "PriceAmount", b.rrp_usd)
                t(pr, "CurrencyCode", "USD")
                pr_terr = ET.SubElement(pr, "Territory")
                t(pr_terr, "CountriesIncluded", "US CA")

    return root


if __name__ == "__main__":
    root = build_onix(BOOKS)
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    output = sys.stdout.buffer if hasattr(sys.stdout, "buffer") else sys.stdout
    output.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    tree.write(output, encoding="utf-8", xml_declaration=False)
    output.write(b"\n")

    print(f"\n<!-- Generated {len(BOOKS)} books -->", file=sys.stderr)
