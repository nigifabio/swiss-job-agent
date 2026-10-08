"""French and German for the platform pages people see (home page, account request, invite, account,
messages). The admin page stays in English. Format: see i18n.py."""

_BASE = [
    ('<html lang="en">', '<html lang="fr">', '<html lang="de">'),
    ('>admin</a>', '>admin</a>', '>Admin</a>'),
]

_WELCOME = [
    ('Swiss Job Agent: your private job-search assistant', 'Swiss Job Agent : votre assistant privé de recherche d\'emploi', 'Swiss Job Agent: Ihr privater Assistent für die Stellensuche'),
    ('<a class="btn small" href="/">Sign in</a>', '<a class="btn small" href="/">Se connecter</a>', '<a class="btn small" href="/">Anmelden</a>'),
    ('<a class="btn small" href="/">My workspace</a> · <a href="{{ switch_url }}">sign out</a>', '<a class="btn small" href="/">Mon espace</a> · <a href="{{ switch_url }}">se déconnecter</a>',
     '<a class="btn small" href="/">Mein Bereich</a> · <a href="{{ switch_url }}">abmelden</a>'),
    ('<a href="{{ switch_url }}">sign in with another address</a>', '<a href="{{ switch_url }}">se connecter avec une autre adresse</a>', '<a href="{{ switch_url }}">mit anderer Adresse anmelden</a>'),
    ('<b>Your request was approved, {{ req.name or email }}.</b>', '<b>Votre demande a été acceptée, {{ req.name or email }}.</b>', '<b>Ihre Anfrage wurde genehmigt, {{ req.name or email }}.</b>'),
    ("Create your private workspace as {{ email }}; you'll set it up from your CV in a few minutes.", "Créez votre espace privé avec {{ email }} ; vous le configurerez à partir de votre CV en quelques minutes.",
     "Erstellen Sie Ihren privaten Bereich als {{ email }}; Sie richten ihn in wenigen Minuten aus Ihrem Lebenslauf ein."),
    ('All workspaces are taken at the moment. Please come back later.', 'Tous les espaces sont pris pour le moment. Merci de revenir plus tard.', 'Im Moment sind alle Bereiche vergeben. Bitte kommen Sie später wieder.'),
    ('<button type="submit">Create my workspace →</button>', '<button type="submit">Créer mon espace →</button>', '<button type="submit">Meinen Bereich erstellen →</button>'),
    ('<b>Your request is waiting for approval.</b>', '<b>Votre demande est en attente de validation.</b>', '<b>Ihre Anfrage wartet auf Genehmigung.</b>'),
    ('You asked for an account as {{ email }} on {{ req.created_at[:10] }}. Come back to this page in a day or two: once approved, a button to create your workspace will be here.',
     'Vous avez demandé un compte avec {{ email }} le {{ req.created_at[:10] }}. Revenez sur cette page dans un jour ou deux : une fois la demande acceptée, un bouton pour créer votre espace sera ici.',
     'Sie haben am {{ req.created_at[:10] }} als {{ email }} ein Konto angefragt. Kommen Sie in ein, zwei Tagen wieder auf diese Seite: Nach der Genehmigung finden Sie hier einen Knopf, um Ihren Bereich zu erstellen.'),
    ("<b>You're signed in as {{ email }}, but you don't have a workspace yet.</b>", "<b>Vous êtes connecté·e avec {{ email }}, mais vous n'avez pas encore d'espace.</b>",
     "<b>Sie sind als {{ email }} angemeldet, haben aber noch keinen Bereich.</b>"),
    ('This service is by invitation. Open the invite link you were sent while signed in with this address{% if contact %}, or <a href="mailto:{{ contact }}">ask for an invite</a>{% endif %}. '
     'If your workspace is under another address (for example your Hotmail instead of your Gmail), sign in with that one.',
     'Ce service est sur invitation. Ouvrez le lien d\'invitation reçu en étant connecté·e avec cette adresse{% if contact %}, ou <a href="mailto:{{ contact }}">demandez une invitation</a>{% endif %}. '
     'Si votre espace est lié à une autre adresse (par exemple Hotmail au lieu de Gmail), connectez-vous avec celle-ci.',
     'Dieser Dienst ist nur auf Einladung. Öffnen Sie den erhaltenen Einladungslink, während Sie mit dieser Adresse angemeldet sind{% if contact %}, oder <a href="mailto:{{ contact }}">bitten Sie um eine Einladung</a>{% endif %}. '
     'Wenn Ihr Bereich unter einer anderen Adresse läuft (zum Beispiel Hotmail statt Gmail), melden Sie sich mit dieser an.'),
    ('<a class="btn" href="/_platform/request">Request an account →</a>', '<a class="btn" href="/_platform/request">Demander un compte →</a>', '<a class="btn" href="/_platform/request">Konto anfragen →</a>'),
    ('<a class="btn ghost" href="{{ switch_url }}">Sign in with another address</a>', '<a class="btn ghost" href="{{ switch_url }}">Se connecter avec une autre adresse</a>',
     '<a class="btn ghost" href="{{ switch_url }}">Mit anderer Adresse anmelden</a>'),
    ('<h2>Your private assistant for a job search in Switzerland</h2>', '<h2>Votre assistant privé pour chercher un emploi en Suisse</h2>', '<h2>Ihr privater Assistent für die Stellensuche in der Schweiz</h2>'),
    ('It scans Swiss job boards and company career pages for you, ranks every posting against your skills, keeps track of your applications, and writes a tailored CV and cover letter for each job. '
     'Built for people registered with an ORP / RAV office: the monthly proof-of-search report is one click.',
     'Il parcourt pour vous les sites d\'emploi suisses et les pages carrière des entreprises, classe chaque annonce selon vos compétences, suit vos candidatures et rédige un CV adapté et une lettre de motivation pour chaque poste. '
     'Conçu pour les personnes inscrites à un ORP : les preuves de recherches mensuelles en un clic.',
     'Er durchsucht für Sie Schweizer Stellenportale und Karriereseiten, ordnet jedes Inserat nach Ihren Kompetenzen, behält Ihre Bewerbungen im Blick und schreibt zu jeder Stelle einen angepassten Lebenslauf und ein Motivationsschreiben. '
     'Gemacht für Personen, die beim RAV angemeldet sind: der monatliche Nachweis der Arbeitsbemühungen mit einem Klick.'),
    ('<a class="btn" href="/">Open my workspace →</a>', '<a class="btn" href="/">Ouvrir mon espace →</a>', '<a class="btn" href="/">Meinen Bereich öffnen →</a>'),
    ('<a class="btn" href="/">Sign in →</a><a class="btn ghost" href="/_platform/request">Request an account</a>', '<a class="btn" href="/">Se connecter →</a><a class="btn ghost" href="/_platform/request">Demander un compte</a>',
     '<a class="btn" href="/">Anmelden →</a><a class="btn ghost" href="/_platform/request">Konto anfragen</a>'),
    ('rel="noopener">Source code on GitHub</a>', 'rel="noopener">Code source sur GitHub</a>', 'rel="noopener">Quellcode auf GitHub</a>'),
    ('<h3>Find</h3><p>jobs.ch, jobup.ch, Job-Room (work.swiss), company career sites and remote boards, scanned twice a day. The same job from several sites appears once.</p>',
     '<h3>Trouver</h3><p>jobs.ch, jobup.ch, Job-Room (travail.swiss), l\'État de Vaud, la Confédération et des sites carrière d\'entreprises, parcourus deux fois par jour. La même offre venant de plusieurs sites n\'apparaît qu\'une fois.</p>',
     '<h3>Finden</h3><p>jobs.ch, jobup.ch, Job-Room (arbeit.swiss), Kanton Waadt, Bund und Karriereseiten von Unternehmen, zweimal täglich durchsucht. Dieselbe Stelle von mehreren Portalen erscheint nur einmal.</p>'),
    ('<h3>Rank</h3><p>A 0-100 match score from your own skills. Mark skills you have, or words you want to avoid, straight from a posting.</p>',
     '<h3>Classer</h3><p>Un score de 0 à 100 d\'après vos propres compétences. Indiquez les compétences que vous avez, ou les mots à éviter, directement depuis une annonce.</p>',
     '<h3>Ordnen</h3><p>Eine Punktzahl von 0 bis 100 anhand Ihrer eigenen Kompetenzen. Kompetenzen, die Sie haben, oder Wörter, die Sie vermeiden wollen, markieren Sie direkt im Inserat.</p>'),
    ('<h3>Track</h3><p>New, shortlisted, applied, interview, offer: with contacts, notes and follow-up reminders.</p>',
     '<h3>Suivre</h3><p>Nouvelles, à retenir, postulé, entretien, offre : avec contacts, notes et rappels de relance.</p>',
     '<h3>Verfolgen</h3><p>Neu, gemerkt, beworben, Gespräch, Angebot: mit Kontakten, Notizen und Erinnerungen zum Nachfassen.</p>'),
    ("<h3>Write</h3><p>A CV and a Swiss-format cover letter per job, in the posting's language, using only facts from your own profile. Nothing is invented.</p>",
     "<h3>Rédiger</h3><p>Un CV et une lettre de motivation au format suisse pour chaque poste, dans la langue de l'annonce, uniquement à partir des faits de votre profil. Rien n'est inventé.</p>",
     "<h3>Schreiben</h3><p>Ein Lebenslauf und ein Motivationsschreiben im Schweizer Format pro Stelle, in der Sprache des Inserats, nur mit Fakten aus Ihrem Profil. Nichts wird erfunden.</p>"),
    ('<h3>Report</h3><p>The ORP / RAV "preuves de recherches" for a week or a month as PDF or Excel, and your numbers against the monthly target.</p>',
     '<h3>Justifier</h3><p>Les preuves de recherches pour l\'ORP, sur le formulaire officiel ou en Excel, et vos chiffres par rapport à l\'objectif mensuel.</p>',
     '<h3>Nachweisen</h3><p>Der Nachweis der Arbeitsbemühungen fürs RAV als offizielles Formular oder Excel, und Ihre Zahlen im Vergleich zum Monatsziel.</p>'),
    ('<h3>How to start</h3>', '<h3>Pour commencer</h3>', '<h3>So starten Sie</h3>'),
    ('<b>Request an account</b> (or open the invite link you were sent) and sign in with your Google account, or with a code sent to your e-mail. No new password.',
     '<b>Demandez un compte</b> (ou ouvrez le lien d\'invitation reçu) et connectez-vous avec votre compte Google ou avec un code envoyé par e-mail. Aucun nouveau mot de passe.',
     '<b>Fragen Sie ein Konto an</b> (oder öffnen Sie den erhaltenen Einladungslink) und melden Sie sich mit Ihrem Google-Konto oder mit einem per E-Mail gesendeten Code an. Kein neues Passwort.'),
    ('<b>Upload your CV</b> (PDF or Word) and/or your LinkedIn profile. Check what was read and correct it.', '<b>Importez votre CV</b> (PDF ou Word) et/ou votre profil LinkedIn. Vérifiez ce qui a été lu et corrigez-le.',
     '<b>Laden Sie Ihren Lebenslauf hoch</b> (PDF oder Word) und/oder Ihr LinkedIn-Profil. Prüfen und korrigieren Sie, was gelesen wurde.'),
    ("<b>Choose what you're looking for</b>: roles, town, how far you'd commute, languages. Your search is built from that.",
     "<b>Indiquez ce que vous cherchez</b> : postes, localité, distance acceptable, langues. Votre recherche est construite à partir de cela.",
     "<b>Wählen Sie, was Sie suchen</b>: Funktionen, Ort, wie weit Sie pendeln würden, Sprachen. Daraus wird Ihre Suche erstellt."),
    ('<b>Read your first results</b> a few minutes later, and generate your first CV and letter.', '<b>Consultez vos premiers résultats</b> quelques minutes plus tard, et générez votre premier CV et votre première lettre.',
     '<b>Sehen Sie Ihre ersten Ergebnisse</b> wenige Minuten später und erstellen Sie Ihren ersten Lebenslauf und Brief.'),
    ("<h3>Private</h3><p>Each person gets a separate workspace with its own database. Other users can't see your data, and the administrator has no page to look into it: only totals (how many jobs, when the last search ran, when you last signed in).</p>",
     "<h3>Privé</h3><p>Chaque personne a un espace séparé avec sa propre base de données. Les autres utilisateurs ne voient pas vos données, et l'administrateur n'a aucune page pour les consulter : il ne voit que des totaux (nombre d'offres, date de la dernière recherche, date de votre dernière connexion).</p>",
     "<h3>Privat</h3><p>Jede Person erhält einen eigenen Bereich mit eigener Datenbank. Andere Nutzer sehen Ihre Daten nicht, und der Administrator hat keine Seite, um hineinzuschauen: Er sieht nur Summen (Anzahl Stellen, Zeitpunkt der letzten Suche, Zeitpunkt Ihrer letzten Anmeldung).</p>"),
    ('<h3>Yours</h3><p>Download everything, or delete your workspace, at any time from the Account page.</p>',
     '<h3>À vous</h3><p>Téléchargez tout, ou supprimez votre espace, à tout moment depuis la page Compte.</p>',
     '<h3>Ihres</h3><p>Laden Sie jederzeit alles herunter oder löschen Sie Ihren Bereich über die Seite Konto.</p>'),
    ('<h3>No AI service, no tracking</h3><p>Your CV is never sent to an AI or to a third party. The only outside requests go to the job sites being searched and to the public-transport timetable.</p>',
     '<h3>Pas d\'IA externe, pas de pistage</h3><p>Votre CV n\'est jamais envoyé à une IA ni à un tiers. Les seules requêtes externes vont aux sites d\'emploi consultés et à l\'horaire des transports publics.</p>',
     '<h3>Kein KI-Dienst, kein Tracking</h3><p>Ihr Lebenslauf wird nie an eine KI oder an Dritte gesendet. Anfragen nach aussen gehen nur an die durchsuchten Stellenportale und den Fahrplan.</p>'),
    ('<h3>You apply, not a robot</h3><p>It never logs into your accounts and never sends an application for you.</p>',
     '<h3>C\'est vous qui postulez</h3><p>Il ne se connecte jamais à vos comptes et n\'envoie jamais de candidature à votre place.</p>',
     '<h3>Sie bewerben sich, kein Roboter</h3><p>Er meldet sich nie in Ihren Konten an und sendet nie eine Bewerbung für Sie.</p>'),
    ('<h3>Open source</h3>', '<h3>Logiciel libre</h3>', '<h3>Open Source</h3>'),
    ('Swiss Job Agent is free software under the MIT licence. You can read the code, report a problem, or run your own copy on your computer or server:',
     'Swiss Job Agent est un logiciel libre sous licence MIT. Vous pouvez lire le code, signaler un problème ou installer votre propre copie sur votre ordinateur ou serveur :',
     'Swiss Job Agent ist freie Software unter der MIT-Lizenz. Sie können den Code lesen, ein Problem melden oder eine eigene Kopie auf Ihrem Computer oder Server betreiben:'),
]

_REQUEST = [
    ('Request an account · Swiss Job Agent', 'Demander un compte · Swiss Job Agent', 'Konto anfragen · Swiss Job Agent'),
    ('← back</a>', '← retour</a>', '← zurück</a>'),
    ('Request an account</h2>', 'Demander un compte</h2>', 'Konto anfragen</h2>'),
    ("You're signed in as <b>{{ email }}</b>. Your workspace will be created under this address once the request is approved.",
     "Vous êtes connecté·e avec <b>{{ email }}</b>. Votre espace sera créé sous cette adresse une fois la demande acceptée.",
     "Sie sind als <b>{{ email }}</b> angemeldet. Ihr Bereich wird unter dieser Adresse erstellt, sobald die Anfrage genehmigt ist."),
    ('<label>Your name<br>', '<label>Votre nom<br>', '<label>Ihr Name<br>'),
    ('What kind of job are you looking for, and where? <span class="muted">(optional)</span>', 'Quel type d\'emploi cherchez-vous, et où ? <span class="muted">(facultatif)</span>',
     'Was für eine Stelle suchen Sie, und wo? <span class="muted">(freiwillig)</span>'),
    ('>Send my request →</button>', '>Envoyer ma demande →</button>', '>Anfrage senden →</button>'),
    ('Only your name, this address and your message are sent to the person who runs the service.', 'Seuls votre nom, cette adresse et votre message sont transmis à la personne qui gère le service.',
     'Nur Ihr Name, diese Adresse und Ihre Nachricht gehen an die Person, die den Dienst betreibt.'),
]

_INVITE = [
    ("You're invited</h2>", 'Vous êtes invité·e</h2>', 'Sie sind eingeladen</h2>'),
    ('Create your private job-search workspace as <b>{{ email }}</b>', 'Créez votre espace privé de recherche d\'emploi avec <b>{{ email }}</b>', 'Erstellen Sie Ihren privaten Bereich für die Stellensuche als <b>{{ email }}</b>'),
    ('It runs in its own isolated space: nobody else using this service can see your data.', 'Il fonctionne dans un espace isolé : aucun autre utilisateur du service ne voit vos données.',
     'Er läuft in einem eigenen, abgetrennten Bereich: Niemand sonst, der den Dienst nutzt, sieht Ihre Daten.'),
    ("You'll set it up in a few minutes from your CV and/or your LinkedIn profile.", 'Vous le configurerez en quelques minutes à partir de votre CV et/ou de votre profil LinkedIn.',
     'Sie richten ihn in wenigen Minuten aus Ihrem Lebenslauf und/oder Ihrem LinkedIn-Profil ein.'),
    ('You can download or delete all your data at any time (Account page).', 'Vous pouvez télécharger ou supprimer toutes vos données à tout moment (page Compte).',
     'Sie können jederzeit alle Ihre Daten herunterladen oder löschen (Seite Konto).'),
    ('>Create my workspace →</button>', '>Créer mon espace →</button>', '>Meinen Bereich erstellen →</button>'),
]

_ME = [
    ('← back to my job search</a>', '← retour à ma recherche d\'emploi</a>', '← zurück zu meiner Stellensuche</a>'),
    ('My account</h2>', 'Mon compte</h2>', 'Mein Konto</h2>'),
    ('Signed in as <b>{{ email }}</b> · workspace <code>{{ t.slug }}</code> · created {{ t.created_at[:10] }}', 'Connecté·e avec <b>{{ email }}</b> · espace <code>{{ t.slug }}</code> · créé le {{ t.created_at[:10] }}',
     'Angemeldet als <b>{{ email }}</b> · Bereich <code>{{ t.slug }}</code> · erstellt am {{ t.created_at[:10] }}'),
    ('Download my data</h3>', 'Télécharger mes données</h3>', 'Meine Daten herunterladen</h3>'),
    ('Everything in your workspace: profile, settings, jobs and applications (SQLite), generated CVs and letters.', 'Tout le contenu de votre espace : profil, réglages, offres et candidatures (SQLite), CV et lettres générés.',
     'Alles in Ihrem Bereich: Profil, Einstellungen, Stellen und Bewerbungen (SQLite), erstellte Lebensläufe und Briefe.'),
    ('>Download (.tar.gz)</a>', '>Télécharger (.tar.gz)</a>', '>Herunterladen (.tar.gz)</a>'),
    ('Delete my workspace</h3>', 'Supprimer mon espace</h3>', 'Meinen Bereich löschen</h3>'),
    ("Removes your workspace and all its data. This can't be undone from here.", "Supprime votre espace et toutes ses données. Cette action est irréversible depuis ici.",
     "Entfernt Ihren Bereich mit allen Daten. Das lässt sich von hier aus nicht rückgängig machen."),
    ('placeholder="Type DELETE"', 'placeholder="Tapez DELETE"', 'placeholder="DELETE eingeben"'),
    ('>Delete everything</button>', '>Tout supprimer</button>', '>Alles löschen</button>'),
]

_STARTING = [
    ('Starting your workspace…</h2>', 'Démarrage de votre espace…</h2>', 'Ihr Bereich wird gestartet…</h2>'),
    ('This takes a few seconds. The page reloads by itself.', 'Cela prend quelques secondes. La page se recharge toute seule.', 'Das dauert ein paar Sekunden. Die Seite lädt sich selbst neu.'),
]

_MESSAGE = [
    ('<h2 style="margin-top:0">{{ title }}</h2><p>{{ text }}</p>', '<h2 style="margin-top:0">{{ title | tr }}</h2><p>{{ text | tr }}</p>', '<h2 style="margin-top:0">{{ title | tr }}</h2><p>{{ text | tr }}</p>'),
    ('href="{{ link[0] }}">{{ link[1] }}</a>', 'href="{{ link[0] }}">{{ link[1] | tr }}</a>', 'href="{{ link[0] }}">{{ link[1] | tr }}</a>'),
]

_LEAGUE = [
    ('← back to my job search</a>', "← retour à ma recherche d'emploi</a>", '← zurück zu meiner Stellensuche</a>'),
    ('<h2 style="margin-top:0">🏆 The league</h2>', '<h2 style="margin-top:0">🏆 La ligue</h2>', '<h2 style="margin-top:0">🏆 Die Liga</h2>'),
    ('A friendly race between the people who search for a job here. You earn points for what moves your search forward: sending applications, following up, sorting your list, getting interviews. Every Monday the week starts again at zero.', 'Une course amicale entre les personnes qui cherchent un emploi ici. Vous gagnez des points pour ce qui fait avancer votre recherche : envoyer des candidatures, relancer, trier votre liste, décrocher des entretiens. Chaque lundi, la semaine repart de zéro.', 'Ein freundschaftliches Rennen unter den Leuten, die hier eine Stelle suchen. Punkte gibt es für alles, was Ihre Suche voranbringt: Bewerbungen senden, nachfassen, die Liste sortieren, Gespräche bekommen. Jeden Montag beginnt die Woche wieder bei null.'),
    ('What the others see of you: <b>a nickname you choose, your points, your streak and your badges</b>. Nothing else: not your name or e-mail, not your jobs, not the companies. You can leave at any time and you disappear from the board.', "Ce que les autres voient de vous : <b>un pseudo que vous choisissez, vos points, votre série et vos badges</b>. Rien d'autre : ni votre nom ou e-mail, ni vos offres, ni les entreprises. Vous pouvez quitter à tout moment et vous disparaissez du classement.", 'Was die anderen von Ihnen sehen: <b>einen Spitznamen Ihrer Wahl, Ihre Punkte, Ihre Serie und Ihre Abzeichen</b>. Sonst nichts: weder Name noch E-Mail, weder Ihre Stellen noch die Firmen. Sie können jederzeit austreten und verschwinden aus der Rangliste.'),
    ("That nickname can't be used: 2 to 20 letters or digits, and not one somebody already has.", 'Ce pseudo ne peut pas être utilisé : 2 à 20 lettres ou chiffres, et pas un pseudo déjà pris.', 'Dieser Spitzname geht nicht: 2 bis 20 Buchstaben oder Ziffern, und keiner, den schon jemand hat.'),
    ('<label>Your nickname<br>', '<label>Votre pseudo<br>', '<label>Ihr Spitzname<br>'),
    ('<button type="submit">Join the league →</button>', '<button type="submit">Rejoindre la ligue →</button>', '<button type="submit">Der Liga beitreten →</button>'),
    ('{{ members }} in the league so far.', '{{ members }} dans la ligue pour le moment.', 'Bisher {{ members }} in der Liga.'),
    ('🏆 The league <span class="muted">· this week</span>', '🏆 La ligue <span class="muted">· cette semaine</span>', '🏆 Die Liga <span class="muted">· diese Woche</span>'),
    ("👑 Last week's champion: <b>{{ champion[0] }}</b> with {{ champion[1] }} points.", '👑 Champion de la semaine dernière : <b>{{ champion[0] }}</b> avec {{ champion[1] }} points.', '👑 Champion der letzten Woche: <b>{{ champion[0] }}</b> mit {{ champion[1] }} Punkten.'),
    ('Nobody has scored yet this week. The first application takes the lead!', "Personne n'a encore marqué cette semaine. La première candidature prend la tête !", 'Diese Woche hat noch niemand gepunktet. Die erste Bewerbung übernimmt die Führung!'),
    ('👑 You lead the week. Keep the crown!', '👑 Vous menez la semaine. Gardez la couronne !', '👑 Sie führen diese Woche. Behalten Sie die Krone!'),
    ('You are {{ ahead.week - mine.week }} points behind <b>{{ ahead.name }}</b>. An application is worth 10, a follow-up 5.', 'Vous êtes à {{ ahead.week - mine.week }} points de <b>{{ ahead.name }}</b>. Une candidature vaut 10, une relance 5.', 'Sie liegen {{ ahead.week - mine.week }} Punkte hinter <b>{{ ahead.name }}</b>. Eine Bewerbung zählt 10, ein Nachfassen 5.'),
    ('<span class="muted">(you)</span>', '<span class="muted">(vous)</span>', '<span class="muted">(Sie)</span>'),
    ('· 🔥 {{ r.streak }} weeks in a row', '· 🔥 {{ r.streak }} semaines de suite', '· 🔥 {{ r.streak }} Wochen in Folge'),
    ('· 💤 still in the starting blocks', '· 💤 encore dans les starting-blocks', '· 💤 noch in den Startblöcken'),
    ('<small>{{ r.month }} this month · {{ r.total }} in total</small>', '<small>{{ r.month }} ce mois · {{ r.total }} au total</small>', '<small>{{ r.month }} diesen Monat · {{ r.total }} insgesamt</small>'),
    ('Points: application 10 · interview 30 · offer 100 · follow-up 5 · CV or letter written for a job 3 · monthly target 25 · a job sorted with a reason 1. Your own score and next badges are on <a href="/week#score">My week</a>.', 'Points : candidature 10 · entretien 30 · offre 100 · relance 5 · CV ou lettre écrits pour une offre 3 · objectif mensuel 25 · une offre triée avec un motif 1. Votre score et vos prochains badges sont sur <a href="/week#score">Ma semaine</a>.', 'Punkte: Bewerbung 10 · Gespräch 30 · Angebot 100 · Nachfassen 5 · Lebenslauf oder Brief für eine Stelle 3 · Monatsziel 25 · eine Stelle mit Grund sortiert 1. Ihr eigener Punktestand und die nächsten Abzeichen stehen unter <a href="/week#score">Meine Woche</a>.'),
    ('The others see only your nickname (<b>{{ t.league_name }}</b>), points, streak and badges.', 'Les autres ne voient que votre pseudo (<b>{{ t.league_name }}</b>), vos points, votre série et vos badges.', 'Die anderen sehen nur Ihren Spitznamen (<b>{{ t.league_name }}</b>), Punkte, Serie und Abzeichen.'),
    ('<button class="ghost small">Change my nickname</button>', '<button class="ghost small">Changer de pseudo</button>', '<button class="ghost small">Spitznamen ändern</button>'),
    ('<button class="ghost small">Leave the league</button>', '<button class="ghost small">Quitter la ligue</button>', '<button class="ghost small">Liga verlassen</button>'),
]

TEMPLATES = {"base.html": _BASE, "welcome.html": _WELCOME, "request.html": _REQUEST, "invite.html": _INVITE, "me.html": _ME,
             "starting.html": _STARTING, "message.html": _MESSAGE, "league.html": _LEAGUE}

STRINGS = {
    'Warming up': ("À l'échauffement", 'Beim Aufwärmen'),
    'On the move': ('En mouvement', 'In Bewegung'),
    'In the race': ('Dans la course', 'Im Rennen'),
    'Front runner': ('En tête de peloton', 'An der Spitze'),
    'Unstoppable': ('Inarrêtable', 'Nicht zu stoppen'),
    'Lift-off': ('Décollage', 'Abgehoben'),
    'High five': ('Tope là', 'High Five'),
    'Bullseye': ('Dans le mille', 'Volltreffer'),
    'On fire': ('En feu', 'On Fire'),
    'Persistent': ('Persévérant·e', 'Hartnäckig'),
    'Sharp eye': ('Œil de lynx', 'Scharfes Auge'),
    'Made to measure': ('Sur mesure', 'Massgeschneidert'),
    'On stage': ('En scène', 'Auf der Bühne'),
    'Thick skin': ('Peau dure', 'Dickes Fell'),
    'Polished': ('Bien poli', 'Auf Hochglanz'),
    'Jackpot': ('Jackpot', 'Jackpot'),
    "Back": ("Retour", "Zurück"),
    "Workspace paused": ("Espace en pause", "Bereich pausiert"),
    "Your workspace is paused. Contact the administrator.": ("Votre espace est en pause. Contactez l'administrateur.", "Ihr Bereich ist pausiert. Wenden Sie sich an den Administrator."),
    "Something went wrong": ("Une erreur s'est produite", "Etwas ist schiefgelaufen"),
    "Your workspace couldn't be created. The administrator can see it in the log; please try again later.":
        ("Votre espace n'a pas pu être créé. L'administrateur le voit dans le journal ; merci de réessayer plus tard.",
         "Ihr Bereich konnte nicht erstellt werden. Der Administrator sieht es im Protokoll; bitte versuchen Sie es später noch einmal."),
    "Your workspace couldn't be created. The administrator was notified in the log; the invite can be reissued.":
        ("Votre espace n'a pas pu être créé. L'administrateur en est informé ; l'invitation peut être renvoyée.",
         "Ihr Bereich konnte nicht erstellt werden. Der Administrator ist informiert; die Einladung kann neu ausgestellt werden."),
    "Not now": ("Pas maintenant", "Im Moment nicht"),
    "There are many requests waiting already. Please try again in a few days.": ("Beaucoup de demandes sont déjà en attente. Merci de réessayer dans quelques jours.", "Es warten bereits viele Anfragen. Bitte versuchen Sie es in ein paar Tagen wieder."),
    "Not approved yet": ("Pas encore acceptée", "Noch nicht genehmigt"),
    "Your request hasn't been approved yet.": ("Votre demande n'a pas encore été acceptée.", "Ihre Anfrage wurde noch nicht genehmigt."),
    "Full": ("Complet", "Voll"),
    "The platform has reached its number of workspaces. Contact the administrator.": ("La plateforme a atteint son nombre d'espaces. Contactez l'administrateur.", "Die Plattform hat ihre Anzahl Bereiche erreicht. Wenden Sie sich an den Administrator."),
    "Invite not valid": ("Invitation non valable", "Einladung ungültig"),
    "This invite link was already used, has expired or was revoked. Ask for a new one.": ("Ce lien d'invitation a déjà été utilisé, a expiré ou a été révoqué. Demandez-en un nouveau.", "Dieser Einladungslink wurde bereits verwendet, ist abgelaufen oder wurde widerrufen. Bitten Sie um einen neuen."),
    "This invite link can't be used.": ("Ce lien d'invitation ne peut pas être utilisé.", "Dieser Einladungslink kann nicht verwendet werden."),
    "This invite was just used.": ("Cette invitation vient d'être utilisée.", "Diese Einladung wurde soeben verwendet."),
    "Invite for someone else": ("Invitation pour une autre personne", "Einladung für jemand anderen"),
    "Not deleted": ("Non supprimé", "Nicht gelöscht"),
    "Type DELETE to confirm.": ("Tapez DELETE pour confirmer.", "Geben Sie zur Bestätigung DELETE ein."),
    "Deleted": ("Supprimé", "Gelöscht"),
    "Your workspace and its data were deleted. A sealed backup copy is kept by the administrator for 30 days, then removed.":
        ("Votre espace et ses données ont été supprimés. Une copie de sauvegarde scellée est conservée 30 jours par l'administrateur, puis effacée.",
         "Ihr Bereich und seine Daten wurden gelöscht. Eine versiegelte Sicherungskopie bleibt 30 Tage beim Administrator und wird dann entfernt."),
}


# ---- Italian: its own file, same English keys ------------------------------------------------
from . import locales_it as _it  # noqa: E402

TEMPLATES = {name: [e + (_it.TEMPLATES.get(name, {}).get(e[0], ""),) for e in entries] for name, entries in TEMPLATES.items()}
STRINGS = {k: v + (_it.STRINGS.get(k, ""),) for k, v in STRINGS.items()}
