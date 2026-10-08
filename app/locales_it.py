"""Italian interface (see i18n.py and locales.py).

TEMPLATES[file][English fragment exactly as in locales.py] = Italian
STRINGS[English text produced by Python] = Italian
A test fails when a fragment or a text of locales.py has no entry here.
"""

TEMPLATES = {'base.html': {'<html lang="en">': '<html lang="it">',
               '>Jobs</a>': '>Offerte</a>',
               '>Stats</a>': '>Statistiche</a>',
               '>ORP report</a>': '>Rapporto URC</a>',
               '>CV</a>': '>CV</a>',
               '>Settings</a>': '>Impostazioni</a>',
               '+ Add application</a>': '+ Aggiungi una candidatura</a>',
               '>Account</a>': '>Account</a>',
               '</b>My week</a>': '</b>La mia settimana</a>',
               '>Improve</a>': '>Migliorare</a>'},
 '_apply_prompt.html': {'Did you apply to <b>{{ j.title }}</b>?': 'Ti sei candidato a <b>{{ j.title }}</b>?',
                        '✓ Yes, add to Applied': '✓ Sì, aggiungi alle candidature',
                        '>Not yet</button>': '>Non ancora</button>'},
 '_chip.html': {'title="Not one of my skills: stop counting it"': 'title="Non è una mia competenza: non contarla più"',
                'title="I have this skill: count it from now on">+ I have it<': 'title="Ho questa competenza: contala da subito">+ Ce l\'ho<',
                'title="Push jobs that ask for this down the list">⛔ Avoid<': 'title="Fai scendere le offerte che la richiedono">⛔ Evita<',
                'title="Stop penalising this">undo<': 'title="Non penalizzare più">annulla<'},
 'dashboard.html': {'⏳ Scanning…': '⏳ Ricerca in corso…',
                    '↻ Scan now': '↻ Cerca ora',
                    'Looking for new roles, this page refreshes by itself.': 'Ricerca di nuove offerte, la pagina si aggiorna da sola.',
                    'Last scan {{ meta.last_scan_at | replace("T", " ") }} UTC · {{ meta.last_scan_new }} new': 'Ultima ricerca {{ meta.last_scan_at | replace("T", " ") '
                                                                                                                '}} UTC · {{ meta.last_scan_new }} nuove',
                    'No scan yet.': 'Nessuna ricerca finora.',
                    '📌 Assigned by the ORP: apply before the deadline': "📌 Assegnazioni dell'URC: candidati entro il termine",
                    'no deadline set': 'nessun termine indicato',
                    "{{ -a.days_left }} day{{ 's' if a.days_left != -1 }} late": "{{ -a.days_left }} giorn{{ 'i' if a.days_left != -1 else 'o' }} di ritardo",
                    '{% elif a.days_left == 0 %}today{% else %}': '{% elif a.days_left == 0 %}oggi{% else %}',
                    "{{ a.days_left }} day{{ 's' if a.days_left != 1 }} left": "ancora {{ a.days_left }} giorn{{ 'i' if a.days_left != 1 else 'o' }}",
                    '🗓 Proofs of job search for {{ orp.last_month.label }}: hand them in by the 5th': '🗓 Prove delle ricerche di lavoro {{ orp.last_month.label }}: da '
                                                                                                      'consegnare entro il 5',
                    "{{ orp.last_month.n }} application{{ 's' if orp.last_month.n != 1 }} recorded.": "{{ orp.last_month.n }} candidatur{{ 'e' if orp.last_month.n != 1 "
                                                                                                      "else 'a' }} registrat{{ 'e' if orp.last_month.n != 1 else 'a' }}.",
                    '>Open the report</a>': '>Apri il rapporto</a>',
                    "⏳ {{ orp.missing }} more application{{ 's' if orp.missing != 1 }} needed this month": "⏳ Ancora {{ orp.missing }} candidatur{{ 'e' if orp.missing "
                                                                                                           "!= 1 else 'a' }} da fare questo mese",
                    "ORP target {{ orp.month }}: <b>{{ orp.done }} / {{ orp.target }}</b> applications · {{ orp.days_left }} day{{ 's' if orp.days_left != 1 }} left in the month": 'Obiettivo '
                                                                                                                                                                                    'URC '
                                                                                                                                                                                    '{{ '
                                                                                                                                                                                    'orp.month '
                                                                                                                                                                                    '}}: '
                                                                                                                                                                                    '<b>{{ '
                                                                                                                                                                                    'orp.done '
                                                                                                                                                                                    '}} '
                                                                                                                                                                                    '/ '
                                                                                                                                                                                    '{{ '
                                                                                                                                                                                    'orp.target '
                                                                                                                                                                                    '}}</b> '
                                                                                                                                                                                    'candidature '
                                                                                                                                                                                    '· '
                                                                                                                                                                                    'ancora '
                                                                                                                                                                                    '{{ '
                                                                                                                                                                                    'orp.days_left '
                                                                                                                                                                                    '}} '
                                                                                                                                                                                    'giorn{{ '
                                                                                                                                                                                    "'i' "
                                                                                                                                                                                    'if '
                                                                                                                                                                                    'orp.days_left '
                                                                                                                                                                                    '!= '
                                                                                                                                                                                    '1 '
                                                                                                                                                                                    'else '
                                                                                                                                                                                    "'o' "
                                                                                                                                                                                    '}} '
                                                                                                                                                                                    'questo '
                                                                                                                                                                                    'mese',
                    '· ✓ reached': '· ✓ raggiunto',
                    '+ spontaneous application</a>': '+ candidatura spontanea</a>',
                    '✉ No answer yet: time to follow up?': '✉ Ancora nessuna risposta: sollecitare?',
                    'applied {{ w.days_waiting }} days ago': 'candidatura inviata {{ w.days_waiting }} giorni fa',
                    '⏰ Follow-ups due (next 14 days)': '⏰ Solleciti da fare (prossimi 14 giorni)',
                    '⚠ Last scan had problems': "⚠ L'ultima ricerca ha avuto dei problemi",
                    'href="/jobs?status={{ s }}">{{ s }} (': 'href="/jobs?status={{ s }}">{{ s | tr }} (',
                    '{{ j.title or "(untitled)" }}': '{{ j.title or "(senza titolo)" }}',
                    '· added by hand': '· aggiunta a mano',
                    '· applied {{ j.applied_date }}': '· candidatura del {{ j.applied_date }}',
                    '· {{ reasons.get(j.discard_reason, j.discard_reason) }}': '· {{ reasons.get(j.discard_reason, j.discard_reason) | tr }}',
                    '>Open &amp; apply ↗</a>': '>Apri e candidati ↗</a>',
                    '("applied", "✓ Applied"), ("shortlisted", "☆ Shortlist")] + ([("new", "↩ Back to new")]': '("applied", "✓ Candidato"), ("shortlisted", "☆ Da '
                                                                                                               'tenere")] + ([("new", "↩ Rimetti tra le nuove")]',
                    'title="Not for me: grey it out. Click again to remove it from the list."': 'title="Non fa per me: mettila in grigio. Clicca ancora per toglierla '
                                                                                                'dalla lista."',
                    '✕ Not for me</span>': '✕ Non fa per me</span>',
                    '✕ Remove</span>': '✕ Togli</span>',
                    'aria-label="Why? (removes the job)" title="Say why and it is removed. It helps tune the search: see Stats."': 'aria-label="Perché? (toglie '
                                                                                                                                   'l\'offerta)" title="Indica il motivo '
                                                                                                                                   "e l'offerta viene tolta. Aiuta a "
                                                                                                                                   'regolare la ricerca: vedi '
                                                                                                                                   'Statistiche."',
                    '<option value="">Why? …</option>': '<option value="">Perché? …</option>',
                    '<option value="{{ k }}">{{ label }}</option>': '<option value="{{ k }}">{{ label | tr }}</option>',
                    'title="The position is no longer open. If you applied, it counts as a refusal with that reason; otherwise it leaves the list.">⊘ Position filled<': 'title="Il '
                                                                                                                                                                         'posto '
                                                                                                                                                                         'non '
                                                                                                                                                                         'è '
                                                                                                                                                                         'più '
                                                                                                                                                                         'aperto. '
                                                                                                                                                                         'Se '
                                                                                                                                                                         'ti '
                                                                                                                                                                         'eri '
                                                                                                                                                                         'candidato, '
                                                                                                                                                                         'conta '
                                                                                                                                                                         'come '
                                                                                                                                                                         'un '
                                                                                                                                                                         'rifiuto '
                                                                                                                                                                         'con '
                                                                                                                                                                         'questo '
                                                                                                                                                                         'motivo; '
                                                                                                                                                                         'altrimenti '
                                                                                                                                                                         "l'offerta "
                                                                                                                                                                         'esce '
                                                                                                                                                                         'dalla '
                                                                                                                                                                         'lista.">⊘ '
                                                                                                                                                                         'Posto '
                                                                                                                                                                         'occupato<',
                    'title="Bring it back to normal">↩ Keep<': 'title="Riportala alla normalità">↩ Tieni<',
                    'Nothing in “{{ status }}”.': 'Niente in «{{ status | tr }}».',
                    'Press <b>Scan now</b> or add one by hand.': "Clicca su <b>Cerca ora</b> o aggiungi un'offerta a mano.",
                    '📋 My week</a>': '📋 La mia settimana</a>',
                    "{{ done }} job{{ 's' if done != 1 }} moved.": "{{ done }} offert{{ 'e' if done != 1 else 'a' }} spostat{{ 'e' if done != 1 else 'a' }}.",
                    'title="The best-ranked jobs that arrived since your last visit">★ Best new ({{ fresh_n }})</a>': 'title="Le offerte meglio classificate arrivate '
                                                                                                                      'dalla tua ultima visita">★ Migliori nuove ({{ '
                                                                                                                      'fresh_n }})</a>',
                    'The {{ jobs | length }} best-ranked job{{ \'s\' if jobs | length != 1 }} that arrived since your last visit. <a href="/jobs?status=new">See the whole list</a>': 'Le '
                                                                                                                                                                                      '{{ '
                                                                                                                                                                                      'jobs '
                                                                                                                                                                                      '| '
                                                                                                                                                                                      'length '
                                                                                                                                                                                      '}} '
                                                                                                                                                                                      'offerte '
                                                                                                                                                                                      'meglio '
                                                                                                                                                                                      'classificate '
                                                                                                                                                                                      'arrivate '
                                                                                                                                                                                      'dalla '
                                                                                                                                                                                      'tua '
                                                                                                                                                                                      'ultima '
                                                                                                                                                                                      'visita. '
                                                                                                                                                                                      '<a '
                                                                                                                                                                                      'href="/jobs?status=new">Vedi '
                                                                                                                                                                                      'tutta '
                                                                                                                                                                                      'la '
                                                                                                                                                                                      'lista</a>',
                    '> Select all</label>': '> Seleziona tutto</label>',
                    'aria-label="Reason for the selected jobs"': 'aria-label="Motivo per le offerte selezionate"',
                    '✕ Discard the selected</button>': '✕ Scarta la selezione</button>',
                    '☆ Shortlist the selected</button>': '☆ Tieni la selezione</button>',
                    'or discard every job scoring below</span>': 'o scarta tutte le offerte con punteggio inferiore a</span>',
                    'aria-label="Score"': 'aria-label="Punteggio"',
                    "confirm('Discard every job of this list scoring below ' + this.form.below.value + '?')": "confirm('Scartare tutte le offerte di questa lista con "
                                                                                                              "punteggio inferiore a ' + this.form.below.value + '?')",
                    '✕ Discard them</button>': '✕ Scartale</button>',
                    'aria-label="Select this job"': 'aria-label="Seleziona questa offerta"',
                    '<span class="fresh">new</span>': '<span class="fresh">nuova</span>',
                    'Same job also posted by:': 'Stesso posto pubblicato anche da:',
                    'Nothing new since your last visit.': 'Niente di nuovo dalla tua ultima visita.',
                    'placeholder="Keyword: title, company, skill…" aria-label="Keyword"': 'placeholder="Parola chiave: titolo, azienda, competenza…" aria-label="Parola '
                                                                                          'chiave"',
                    'aria-label="Role"><option value="">All roles</option>': 'aria-label="Tipo di posto"><option value="">Tutti i tipi di posto</option>',
                    'aria-label="Found"><option value="">Found: any time</option>': 'aria-label="Trovata"><option value="">Trovata: qualsiasi data</option>',
                    '[(1, "Last 24 hours"), (3, "Last 3 days"), (7, "Last 7 days"), (30, "Last 30 days")]': '[(1, "Ultime 24 ore"), (3, "Ultimi 3 giorni"), (7, "Ultimi '
                                                                                                            '7 giorni"), (30, "Ultimi 30 giorni")]',
                    'aria-label="Distance"><option value="">Any distance</option>': 'aria-label="Distanza"><option value="">Qualsiasi distanza</option>',
                    '>Within {{ k }} km of home</option>': '>Entro {{ k }} km dal domicilio</option>',
                    'aria-label="Order"': 'aria-label="Ordine"',
                    '[("best", "Best match first"), ("newest", "Newest first")] + ([("nearest", "Nearest first")]': '[("best", "Miglior punteggio prima"), ("newest", '
                                                                                                                    '"Più recenti prima")] + ([("nearest", "Più vicine '
                                                                                                                    'prima")]',
                    '<button class="small" type="submit">Search</button>': '<button class="small" type="submit">Cerca</button>',
                    '{{ jobs | length }} of {{ f.total }}</span> <a href="/jobs?status={{ status }}">Clear</a>': '{{ jobs | length }} su {{ f.total }}</span> <a '
                                                                                                                 'href="/jobs?status={{ status }}">Azzera</a>',
                    'No job matches this search. <a href="/jobs?status={{ status }}">Clear</a>': 'Nessuna offerta corrisponde a questa ricerca. <a href="/jobs?status={{ '
                                                                                                 'status }}">Azzera</a>',
                    'title="My score"': 'title="Il mio punteggio"'},
 'detail.html': {'← back to {{ job.status }}</a>': '← torna a «{{ job.status | tr }}»</a>',
                 '>Open &amp; apply ↗</a>': '>Apri e candidati ↗</a>',
                 '✓ Mark as applied': '✓ Segna come candidato',
                 '✓ Applied{% if job.applied_date %} on {{ job.applied_date }}{% endif %}': '✓ Candidato{% if job.applied_date %} il {{ job.applied_date }}{% endif %}',
                 'title="The position is no longer open. If you applied, it counts as a refusal with that reason; otherwise it leaves the list.">⊘ Position filled already<': 'title="Il '
                                                                                                                                                                              'posto '
                                                                                                                                                                              'non '
                                                                                                                                                                              'è '
                                                                                                                                                                              'più '
                                                                                                                                                                              'aperto. '
                                                                                                                                                                              'Se '
                                                                                                                                                                              'ti '
                                                                                                                                                                              'eri '
                                                                                                                                                                              'candidato, '
                                                                                                                                                                              'conta '
                                                                                                                                                                              'come '
                                                                                                                                                                              'un '
                                                                                                                                                                              'rifiuto '
                                                                                                                                                                              'con '
                                                                                                                                                                              'questo '
                                                                                                                                                                              'motivo; '
                                                                                                                                                                              'altrimenti '
                                                                                                                                                                              "l'offerta "
                                                                                                                                                                              'esce '
                                                                                                                                                                              'dalla '
                                                                                                                                                                              'lista.">⊘ '
                                                                                                                                                                              'Posto '
                                                                                                                                                                              'già '
                                                                                                                                                                              'occupato<',
                 'aria-label="Why discard" style="width:auto"><option value="">Why? (optional)</option>': 'aria-label="Perché scartare" style="width:auto"><option '
                                                                                                          'value="">Perché? (facoltativo)</option>',
                 '<option value="{{ k }}">{{ label }}</option>': '<option value="{{ k }}">{{ label | tr }}</option>',
                 '>✕ Discard</button>': '>✕ Scarta</button>',
                 'confirm(\'Never show jobs from {{ job.company | replace("\'", " ") }} again?\')': "confirm('Non mostrare mai più le offerte di {{ job.company | "
                                                                                                    'replace("\'", " ") }}?\')',
                 'title="Hide this company or agency from now on (undo in Settings)">🚫 Never show this company<': 'title="Nascondi questa azienda o agenzia da subito '
                                                                                                                  '(annullabile in Impostazioni)">🚫 Non mostrare più '
                                                                                                                  'questa azienda<',
                 '🎯 Interview preparation sheet': '🎯 Scheda di preparazione al colloquio',
                 'Discarded: {{ reasons.get(job.discard_reason, job.discard_reason) }}': 'Scartata: {{ reasons.get(job.discard_reason, job.discard_reason) | tr }}',
                 '<b>{{ job.commute_min }} min</b> by public transport from {{ home_town }}': '<b>{{ job.commute_min }} min</b> con i trasporti pubblici da {{ home_town '
                                                                                              '}}',
                 '⚠ this posting is no longer online (checked {{ job.closed_at[:10] }})': '⚠ questo annuncio non è più online (verificato il {{ job.closed_at[:10] }})',
                 '💰 Pay is rarely stated: check the usual range for this job with the official calculators': '💰 Il salario è indicato raramente: verifica la fascia '
                                                                                                             'usuale per questo posto con i calcolatori ufficiali',
                 '>national wage calculator ↗</a>': '>calcolatore nazionale dei salari ↗</a>',
                 'This posting mentions:': 'Questo annuncio menziona:',
                 '<span class="flag">{{ label }}</span>': '<span class="flag">{{ label | tr }}</span>',
                 '<span class="muted">{{ cv_note }}</span>': '<span class="muted">{{ cv_note | tr }}</span>',
                 '<strong>Score {{ job.score }}</strong>': '<strong>Punteggio {{ job.score }}</strong>',
                 '>In your CV:</span>': '>Nel tuo CV:</span>',
                 '>Not in your CV:</span>': '>Non nel tuo CV:</span>',
                 '>You avoid:</span>': '>Eviti:</span>',
                 'Your choices re-rank the list now and steer every future scan.': 'Le tue scelte riordinano subito la lista e orientano ogni ricerca futura.',
                 '<label>Status</label>': '<label>Stato</label>',
                 '{% if s == job.status %}selected{% endif %}>{{ s }}</option>': '{% if s == job.status %}selected{% endif %}>{{ s | tr }}</option>',
                 '>Update status</button>': '>Aggiorna lo stato</button>',
                 '<label>Contact</label>': '<label>Contatto</label>',
                 '<label>Recruiter / search firm</label>': '<label>Selezionatore / agenzia</label>',
                 '<label>CV version sent</label>': '<label>Versione del CV inviata</label>',
                 '<label>Applied date</label>': '<label>Data della candidatura</label>',
                 '<label>Follow-up date</label>': '<label>Data del sollecito</label>',
                 '<label>Employment rate</label>': '<label>Grado di occupazione</label>',
                 '<label>How you applied (for the ORP report)</label>': '<label>Modalità di candidatura (per il rapporto URC)</label>',
                 '<label>Refusal reason (if rejected)</label>': '<label>Motivo del rifiuto (se rifiutato)</label>',
                 '> Assigned by the ORP (assignation)</label>': "> Assegnato dall'URC (assegnazione)</label>",
                 '<label>ORP deadline to apply</label>': "<label>Termine dell'URC per candidarsi</label>",
                 '<label>Notes</label>': '<label>Note</label>',
                 '>Save details</button>': '>Salva</button>',
                 '<strong>Follow-up message</strong>': '<strong>Messaggio di sollecito</strong>',
                 '· applied on {{ job.applied_date }}{% if job.followed_up_at %} · followed up on {{ job.followed_up_at }}{% endif %}': '· candidatura del {{ '
                                                                                                                                        'job.applied_date }}{% if '
                                                                                                                                        'job.followed_up_at %} · '
                                                                                                                                        'sollecitato il {{ '
                                                                                                                                        'job.followed_up_at }}{% endif '
                                                                                                                                        '%}',
                 'No answer after a week or two? Copy this into an e-mail (the first line is the subject), adapt it, send it.': 'Nessuna risposta dopo una o due '
                                                                                                                                'settimane? Copia questo testo in '
                                                                                                                                "un'e-mail (la prima riga è l'oggetto), "
                                                                                                                                'adattalo, invialo.',
                 '✓ I sent a follow-up today': '✓ Ho sollecitato oggi',
                 '<strong>Cover letter</strong> <span class="muted">· {{ letter_engine }}</span>': '<strong>Lettera di motivazione</strong> <span class="muted">· {{ '
                                                                                                   'letter_engine | tr }}</span>',
                 '{% if job.letter %}Rewrite letter{% else %}Write cover letter{% endif %}': '{% if job.letter %}Riscrivi la lettera{% else %}Scrivi la lettera di '
                                                                                             'motivazione{% endif %}',
                 '>Save edits</button>': '>Salva le modifiche</button>',
                 'Add a candidate profile (data/profile.json) to write letters.': 'Aggiungi un profilo (data/profile.json) per scrivere le lettere.',
                 '<strong>Status history</strong>': '<strong>Cronologia dello stato</strong>',
                 '<tr><td>{{ h.status }}</td>': '<tr><td>{{ h.status | tr }}</td>',
                 'No changes yet.': 'Nessun cambiamento finora.',
                 '<label>Interview (date and time)</label>': '<label>Colloquio (data e ora)</label>',
                 '<strong>Documents to send</strong>': '<strong>Documenti da inviare</strong>',
                 'ready · tick what is ready for this application</span>': 'pronti · spunta ciò che è pronto per questa candidatura</span>',
                 '<span class="flag">asked in the posting</span>': '<span class="flag">richiesto nell\'annuncio</span>',
                 'Save the list</button>': 'Salva la lista</button>',
                 'Swiss employers usually expect the full file: CV, letter, work certificates and diplomas, in one PDF if you can.': 'I datori di lavoro svizzeri si '
                                                                                                                                     'aspettano di solito il dossier '
                                                                                                                                     'completo: CV, lettera, certificati '
                                                                                                                                     'di lavoro e diplomi, se possibile '
                                                                                                                                     'in un unico PDF.',
                 '📄 CV for this job ↓</a>': '📄 CV per questa offerta ↓</a>',
                 '✉ Cover letter ↓</a>': '✉ Lettera di motivazione ↓</a>',
                 '<strong>CV for this job</strong>': '<strong>CV per questa offerta</strong>',
                 "confirm('Write the CV again from your profile? Your edits to this text will be lost.')": "confirm('Riscrivere il CV a partire dal tuo profilo? Le tue "
                                                                                                           "modifiche a questo testo andranno perse.')",
                 '{% if job.cv_text %}Rewrite the CV{% else %}Write the CV{% endif %}': '{% if job.cv_text %}Riscrivi il CV{% else %}Scrivi il CV{% endif %}',
                 'Open the PDF made earlier ↗</a>': 'Apri il PDF generato in precedenza ↗</a>',
                 'Change anything, then save: the PDF is made from this text exactly as written. A line starting with ## is a section title, ### a job (the next line is its dates), - a point. Your name, contact details and photo come from your profile.': 'Modifica '
                                                                                                                                                                                                                                                               'ciò '
                                                                                                                                                                                                                                                               'che '
                                                                                                                                                                                                                                                               'vuoi, '
                                                                                                                                                                                                                                                               'poi '
                                                                                                                                                                                                                                                               'salva: '
                                                                                                                                                                                                                                                               'il '
                                                                                                                                                                                                                                                               'PDF '
                                                                                                                                                                                                                                                               'è '
                                                                                                                                                                                                                                                               'fatto '
                                                                                                                                                                                                                                                               'da '
                                                                                                                                                                                                                                                               'questo '
                                                                                                                                                                                                                                                               'testo, '
                                                                                                                                                                                                                                                               'così '
                                                                                                                                                                                                                                                               "com'è. "
                                                                                                                                                                                                                                                               'Una '
                                                                                                                                                                                                                                                               'riga '
                                                                                                                                                                                                                                                               'che '
                                                                                                                                                                                                                                                               'inizia '
                                                                                                                                                                                                                                                               'con '
                                                                                                                                                                                                                                                               '## '
                                                                                                                                                                                                                                                               'è '
                                                                                                                                                                                                                                                               'un '
                                                                                                                                                                                                                                                               'titolo '
                                                                                                                                                                                                                                                               'di '
                                                                                                                                                                                                                                                               'sezione, '
                                                                                                                                                                                                                                                               '### '
                                                                                                                                                                                                                                                               'un '
                                                                                                                                                                                                                                                               'impiego '
                                                                                                                                                                                                                                                               '(la '
                                                                                                                                                                                                                                                               'riga '
                                                                                                                                                                                                                                                               'seguente '
                                                                                                                                                                                                                                                               'indica '
                                                                                                                                                                                                                                                               'le '
                                                                                                                                                                                                                                                               'date), '
                                                                                                                                                                                                                                                               '- '
                                                                                                                                                                                                                                                               'un '
                                                                                                                                                                                                                                                               'punto. '
                                                                                                                                                                                                                                                               'Il '
                                                                                                                                                                                                                                                               'tuo '
                                                                                                                                                                                                                                                               'nome, '
                                                                                                                                                                                                                                                               'i '
                                                                                                                                                                                                                                                               'recapiti '
                                                                                                                                                                                                                                                               'e '
                                                                                                                                                                                                                                                               'la '
                                                                                                                                                                                                                                                               'foto '
                                                                                                                                                                                                                                                               'vengono '
                                                                                                                                                                                                                                                               'dal '
                                                                                                                                                                                                                                                               'tuo '
                                                                                                                                                                                                                                                               'profilo.',
                 '<button type="submit">Save and update the PDF</button>': '<button type="submit">Salva e aggiorna il PDF</button>',
                 'aria-label="Start from"': 'aria-label="Partire da"',
                 '>From my profile, tailored to this job</option>': '>Dal mio profilo, adattato a questa offerta</option>',
                 '<a href="/cv/versions">My CV versions</a>\n': '<a href="/cv/versions">Le mie versioni del CV</a>\n',
                 '✓ Kept in <a href="/cv/versions">My CV versions</a>.': '✓ Conservato in <a href="/cv/versions">Le mie versioni del CV</a>.',
                 'Not kept: you have reached the number of versions. Delete one in <a href="/cv/versions">My CV versions</a>.': 'Non conservato: hai raggiunto il numero '
                                                                                                                                'di versioni. Eliminane una in <a '
                                                                                                                                'href="/cv/versions">Le mie versioni del '
                                                                                                                                'CV</a>.',
                 '<label>Keep this text to use it for other jobs: give it a name</label><input name="name" maxlength="60" placeholder="e.g. Dessinatrice, Interior design">': '<label>Conserva '
                                                                                                                                                                              'questo '
                                                                                                                                                                              'testo '
                                                                                                                                                                              'per '
                                                                                                                                                                              'altre '
                                                                                                                                                                              'offerte: '
                                                                                                                                                                              'dagli '
                                                                                                                                                                              'un '
                                                                                                                                                                              'nome</label><input '
                                                                                                                                                                              'name="name" '
                                                                                                                                                                              'maxlength="60" '
                                                                                                                                                                              'placeholder="p. '
                                                                                                                                                                              'es. '
                                                                                                                                                                              'Disegnatrice, '
                                                                                                                                                                              'Architettura '
                                                                                                                                                                              'd\'interni">',
                 'value="version">Save as a version</button>': 'value="version">Salva come versione</button>',
                 'title="New CVs start from this text">★ Save as default</button>': 'title="I nuovi CV partono da questo testo">★ Salva come predefinito</button>',
                 "confirm('Write the letter again? Your edits to this text will be lost.')": "confirm('Riscrivere la lettera? Le tue modifiche a questo testo andranno "
                                                                                             "perse.')",
                 'aria-label="Start the letter from"': 'aria-label="Partire da"',
                 '>From my profile, written for this job</option>': '>Dal mio profilo, scritta per questa offerta</option>',
                 '<a href="/cv/versions#letters">My letters</a>\n': '<a href="/cv/versions#letters">Le mie lettere</a>\n',
                 '✓ Kept in <a href="/cv/versions#letters">My letters</a>.': '✓ Conservata in <a href="/cv/versions#letters">Le mie lettere</a>.',
                 'Not kept: you have reached the number of letters. Delete one in <a href="/cv/versions#letters">My letters</a>.': 'Non conservata: hai raggiunto il '
                                                                                                                                   'numero di lettere. Eliminane una in '
                                                                                                                                   '<a href="/cv/versions#letters">Le '
                                                                                                                                   'mie lettere</a>.',
                 '<label>Keep this letter to use it for other jobs: give it a name</label><input name="name" maxlength="60" placeholder="e.g. Architecture office, Spontaneous">': '<label>Conserva '
                                                                                                                                                                                   'questa '
                                                                                                                                                                                   'lettera '
                                                                                                                                                                                   'per '
                                                                                                                                                                                   'altre '
                                                                                                                                                                                   'offerte: '
                                                                                                                                                                                   'dalle '
                                                                                                                                                                                   'un '
                                                                                                                                                                                   'nome</label><input '
                                                                                                                                                                                   'name="name" '
                                                                                                                                                                                   'maxlength="60" '
                                                                                                                                                                                   'placeholder="p. '
                                                                                                                                                                                   'es. '
                                                                                                                                                                                   'Studio '
                                                                                                                                                                                   'di '
                                                                                                                                                                                   'architettura, '
                                                                                                                                                                                   'Spontanea">',
                 "The company, the job title, the place and the date are replaced by the next job's.": "L'azienda, il titolo del posto, il luogo e la data sono "
                                                                                                       'sostituiti da quelli della prossima offerta.',
                 'value="version">Save as a letter version</button>': 'value="version">Salva come modello di lettera</button>',
                 'title="New letters start from this text">★ Save as default letter</button>': 'title="Le nuove lettere partono da questo testo">★ Salva come lettera '
                                                                                               'predefinita</button>',
                 'value="pdf" formtarget="_blank">Save and open the PDF ↗</button>': 'value="pdf" formtarget="_blank">Salva e apri il PDF ↗</button>',
                 '>Save and download the PDF</button>': '>Salva e scarica il PDF</button>'},
 'add.html': {'← back</a>': '← indietro</a>',
              '+ Spontaneous application</h2>': '+ Candidatura spontanea</h2>',
              'You wrote to a company that had no posting. It counts as a job search in your ORP report.': "Hai scritto a un'azienda che non aveva un annuncio. Conta "
                                                                                                           'come ricerca di lavoro nel tuo rapporto URC.',
              'A job with a posting instead →</a>': "Piuttosto un'offerta con annuncio →</a>",
              '<label>Company *</label>': '<label>Azienda *</label>',
              '<label>Town</label>': '<label>Località</label>',
              '<label>For what kind of job</label>': '<label>Per quale tipo di posto</label>',
              '<label>Contact person</label>': '<label>Persona di contatto</label>',
              '<label>Date sent</label>': '<label>Data di invio</label>',
              '<label>How</label>': '<label>Come</label>',
              '<label>Company website (optional)</label>': "<label>Sito dell'azienda (facoltativo)</label>",
              '<label>Notes</label>': '<label>Note</label>',
              '>Add to my applications</button>': '>Aggiungi alle mie candidature</button>',
              '+ Add application</h2>': '+ Aggiungi una candidatura</h2>',
              'For roles you found yourself — LinkedIn, a recruiter, a referral, or a direct posting.': 'Per i posti trovati da te: LinkedIn, un selezionatore, una '
                                                                                                        'segnalazione o un annuncio diretto.',
              'A spontaneous application (no posting) →</a>': 'Una candidatura spontanea (senza annuncio) →</a>',
              '<label>Title *</label>': '<label>Titolo del posto *</label>',
              '<label>Company</label>': '<label>Azienda</label>',
              '<label>Location</label>': '<label>Luogo</label>',
              'placeholder="LinkedIn / direct posting link"': 'placeholder="Link LinkedIn / annuncio diretto"',
              '<label>Source</label>': '<label>Fonte</label>',
              '<label>Status</label>': '<label>Stato</label>',
              "{% if s == 'shortlisted' %}selected{% endif %}>{{ s }}</option>": "{% if s == 'shortlisted' %}selected{% endif %}>{{ s | tr }}</option>",
              '<label>Notes / description</label>': '<label>Note / descrizione</label>',
              '<p><button type="submit">Add</button></p>': '<p><button type="submit">Aggiungi</button></p>'},
 'report.html': {'← previous</a>': '← precedente</a>',
                 '>next →</a>': '>successivo →</a>',
                 '>this month</a>': '>questo mese</a>',
                 'title="The unemployment-insurance form 716.007, filled in with these applications. Add your AVS number, date and signature.">Official ORP form (PDF)</a>': 'title="Il '
                                                                                                                                                                             'formulario '
                                                                                                                                                                             '716.007 '
                                                                                                                                                                             "dell'assicurazione "
                                                                                                                                                                             'contro '
                                                                                                                                                                             'la '
                                                                                                                                                                             'disoccupazione, '
                                                                                                                                                                             'compilato '
                                                                                                                                                                             'con '
                                                                                                                                                                             'queste '
                                                                                                                                                                             'candidature. '
                                                                                                                                                                             'Aggiungi '
                                                                                                                                                                             'il '
                                                                                                                                                                             'tuo '
                                                                                                                                                                             'numero '
                                                                                                                                                                             'AVS, '
                                                                                                                                                                             'la '
                                                                                                                                                                             'data '
                                                                                                                                                                             'e '
                                                                                                                                                                             'la '
                                                                                                                                                                             'firma.">Formulario '
                                                                                                                                                                             'ufficiale '
                                                                                                                                                                             'URC '
                                                                                                                                                                             '(PDF)</a>',
                 "{{ 'Summary PDF' if kind == 'month' else 'PDF' }}": "{{ 'PDF riassuntivo' if kind == 'month' else 'PDF' }}",
                 '>CSV (Excel)</a>': '>CSV (Excel)</a>',
                 'onclick="window.print()">Print</button>': 'onclick="window.print()">Stampa</button>',
                 'No applications in this period. Mark jobs as applied to fill it.': 'Nessuna candidatura in questo periodo. Segna delle offerte come candidate per '
                                                                                     'compilarlo.',
                 "Copy these rows into Job-Room (work.swiss) or attach the PDF to the official form, as your ORP asks, by the 5th of the following month. Contact person, employment rate, how you applied and ORP assignment come from each job's page.": 'Riporta '
                                                                                                                                                                                                                                                           'queste '
                                                                                                                                                                                                                                                           'righe '
                                                                                                                                                                                                                                                           'in '
                                                                                                                                                                                                                                                           'Job-Room '
                                                                                                                                                                                                                                                           '(lavoro.swiss) '
                                                                                                                                                                                                                                                           'o '
                                                                                                                                                                                                                                                           'consegna '
                                                                                                                                                                                                                                                           'il '
                                                                                                                                                                                                                                                           'formulario '
                                                                                                                                                                                                                                                           'ufficiale, '
                                                                                                                                                                                                                                                           'secondo '
                                                                                                                                                                                                                                                           'le '
                                                                                                                                                                                                                                                           'indicazioni '
                                                                                                                                                                                                                                                           'del '
                                                                                                                                                                                                                                                           'tuo '
                                                                                                                                                                                                                                                           'URC, '
                                                                                                                                                                                                                                                           'al '
                                                                                                                                                                                                                                                           'più '
                                                                                                                                                                                                                                                           'tardi '
                                                                                                                                                                                                                                                           'il '
                                                                                                                                                                                                                                                           '5 '
                                                                                                                                                                                                                                                           'del '
                                                                                                                                                                                                                                                           'mese '
                                                                                                                                                                                                                                                           'successivo. '
                                                                                                                                                                                                                                                           'La '
                                                                                                                                                                                                                                                           'persona '
                                                                                                                                                                                                                                                           'di '
                                                                                                                                                                                                                                                           'contatto, '
                                                                                                                                                                                                                                                           'il '
                                                                                                                                                                                                                                                           'grado '
                                                                                                                                                                                                                                                           'di '
                                                                                                                                                                                                                                                           'occupazione, '
                                                                                                                                                                                                                                                           'la '
                                                                                                                                                                                                                                                           'modalità '
                                                                                                                                                                                                                                                           'di '
                                                                                                                                                                                                                                                           'candidatura '
                                                                                                                                                                                                                                                           'e '
                                                                                                                                                                                                                                                           "l'assegnazione "
                                                                                                                                                                                                                                                           'URC '
                                                                                                                                                                                                                                                           'vengono '
                                                                                                                                                                                                                                                           'dalla '
                                                                                                                                                                                                                                                           'pagina '
                                                                                                                                                                                                                                                           'di '
                                                                                                                                                                                                                                                           'ogni '
                                                                                                                                                                                                                                                           'offerta.'},
 'stats.html': {'Job search statistics</h2>': 'Statistiche della ricerca di lavoro</h2>',
                'applications this month (ORP target)': 'candidature questo mese (obiettivo URC)',
                '<div class="l">this week</div>': '<div class="l">questa settimana</div>',
                'applications in total': 'candidature in totale',
                '<div class="l">got an answer</div>': '<div class="l">hanno ricevuto una risposta</div>',
                'led to an interview': 'hanno portato a un colloquio',
                'days to first answer (avg)': 'giorni fino alla prima risposta (media)',
                '<div class="l">waiting for an answer</div>': '<div class="l">in attesa di risposta</div>',
                '<strong>Applications per week</strong> <span class="muted">· last 12 weeks · click a week for its ORP report</span>': '<strong>Candidature per '
                                                                                                                                       'settimana</strong> <span '
                                                                                                                                       'class="muted">· ultime 12 '
                                                                                                                                       'settimane · clicca su una '
                                                                                                                                       'settimana per il suo rapporto '
                                                                                                                                       'URC</span>',
                'title="Week {{ k[-2:] }}: {{ n }} application{{ \'s\' if n != 1 }}">': 'title="Settimana {{ k[-2:] }}: {{ n }} candidatur{{ \'e\' if n != 1 else \'a\' '
                                                                                        '}}">',
                '<span class="x">W{{ k[-2:] }}</span>': '<span class="x">S{{ k[-2:] }}</span>',
                '<strong>Applications per month</strong> <span class="muted">· last 12 months · target {{ s.target }}/month</span>': '<strong>Candidature per '
                                                                                                                                     'mese</strong> <span '
                                                                                                                                     'class="muted">· ultimi 12 mesi · '
                                                                                                                                     'obiettivo {{ s.target '
                                                                                                                                     '}}/mese</span>',
                'title="{{ k }}: {{ n }} application{{ \'s\' if n != 1 }}">': 'title="{{ k }}: {{ n }} candidatur{{ \'e\' if n != 1 else \'a\' }}">',
                '<strong>Funnel</strong>': '<strong>Imbuto</strong>',
                '<div class="hbar" title="{{ label }}: {{ n }}"><span class="lab">{{ label }}</span>': '<div class="hbar" title="{{ label | tr }}: {{ n }}"><span '
                                                                                                       'class="lab">{{ label | tr }}</span>',
                'Rejected: {{ s.rejected }} · pending: {{ s.pending }}': 'Rifiuti: {{ s.rejected }} · in attesa: {{ s.pending }}',
                '<strong>Where your applications came from</strong>': '<strong>Da dove vengono le tue candidature</strong>',
                'No applications yet.': 'Ancora nessuna candidatura.',
                '>How you applied</strong>': '>Modalità di candidatura</strong>',
                '<strong>Why jobs were discarded</strong>': '<strong>Perché delle offerte sono state scartate</strong>',
                '· {{ discards.total }} discarded, {{ discards.with_reason }} with a reason': '· {{ discards.total }} scartate, di cui {{ discards.with_reason }} con un '
                                                                                              'motivo',
                '>download the list (CSV)</a>': '>scarica la lista (CSV)</a>',
                '<tr><th>Reason</th><th>Jobs</th><th>Mostly from</th><th>What to change in <a href="/settings">Settings</a></th></tr>': '<tr><th>Motivo</th><th>Offerte</th><th>Soprattutto '
                                                                                                                                        'da</th><th>Cosa cambiare nelle '
                                                                                                                                        '<a '
                                                                                                                                        'href="/settings">Impostazioni</a></th></tr>',
                '<td>{{ r.label }}</td>': '<td>{{ r.label | tr }}</td>',
                '<td>{{ r.hint }}': '<td>{{ r.hint | tr }}',
                '"skip titles with “" ~ w ~ "” (" ~ n ~ ")"': '"ignora i titoli con «" ~ w ~ "» (" ~ n ~ ")"',
                '"stop searching in " ~ (t | title) ~ " (" ~ n ~ ")"': '"non cercare più a " ~ (t | title) ~ " (" ~ n ~ ")"',
                '"never show " ~ c ~ " (" ~ n ~ ")"': '"non mostrare più " ~ c ~ " (" ~ n ~ ")"',
                'Nothing discarded yet. When you remove a job from a list, choose a reason in the <b>Why?</b> menu: this table then shows what to change so fewer unsuitable jobs come in.': 'Niente '
                                                                                                                                                                                             'di '
                                                                                                                                                                                             'scartato '
                                                                                                                                                                                             'finora. '
                                                                                                                                                                                             'Quando '
                                                                                                                                                                                             'togli '
                                                                                                                                                                                             "un'offerta "
                                                                                                                                                                                             'da '
                                                                                                                                                                                             'una '
                                                                                                                                                                                             'lista, '
                                                                                                                                                                                             'scegli '
                                                                                                                                                                                             'un '
                                                                                                                                                                                             'motivo '
                                                                                                                                                                                             'nel '
                                                                                                                                                                                             'menu '
                                                                                                                                                                                             '<b>Perché?</b>: '
                                                                                                                                                                                             'questa '
                                                                                                                                                                                             'tabella '
                                                                                                                                                                                             'indica '
                                                                                                                                                                                             'allora '
                                                                                                                                                                                             'cosa '
                                                                                                                                                                                             'cambiare '
                                                                                                                                                                                             'per '
                                                                                                                                                                                             'ricevere '
                                                                                                                                                                                             'meno '
                                                                                                                                                                                             'offerte '
                                                                                                                                                                                             'inadatte.',
                '>ORP report for this month →</a>': '>Rapporto URC di questo mese →</a>',
                '>this week</a>': '>questa settimana</a>'},
 'cv.html': {'Skills &amp; preferences</h2>': 'Competenze e preferenze</h2>',
             'These drive the match score and the ranking of every scan. Refine them here or with the buttons on each job page. Skills you add count for scoring; they are only put on a generated CV if your profile mentions them.': 'Determinano '
                                                                                                                                                                                                                                       'il '
                                                                                                                                                                                                                                       'punteggio '
                                                                                                                                                                                                                                       'e '
                                                                                                                                                                                                                                       'la '
                                                                                                                                                                                                                                       'classifica '
                                                                                                                                                                                                                                       'di '
                                                                                                                                                                                                                                       'ogni '
                                                                                                                                                                                                                                       'ricerca. '
                                                                                                                                                                                                                                       'Affinale '
                                                                                                                                                                                                                                       'qui '
                                                                                                                                                                                                                                       'o '
                                                                                                                                                                                                                                       'con '
                                                                                                                                                                                                                                       'i '
                                                                                                                                                                                                                                       'pulsanti '
                                                                                                                                                                                                                                       'di '
                                                                                                                                                                                                                                       'ogni '
                                                                                                                                                                                                                                       'offerta. '
                                                                                                                                                                                                                                       'Le '
                                                                                                                                                                                                                                       'competenze '
                                                                                                                                                                                                                                       'aggiunte '
                                                                                                                                                                                                                                       'contano '
                                                                                                                                                                                                                                       'per '
                                                                                                                                                                                                                                       'il '
                                                                                                                                                                                                                                       'punteggio; '
                                                                                                                                                                                                                                       'compaiono '
                                                                                                                                                                                                                                       'su '
                                                                                                                                                                                                                                       'un '
                                                                                                                                                                                                                                       'CV '
                                                                                                                                                                                                                                       'generato '
                                                                                                                                                                                                                                       'solo '
                                                                                                                                                                                                                                       'se '
                                                                                                                                                                                                                                       'il '
                                                                                                                                                                                                                                       'tuo '
                                                                                                                                                                                                                                       'profilo '
                                                                                                                                                                                                                                       'le '
                                                                                                                                                                                                                                       'menziona.',
             '>Avoided:</span>': '>Evitate:</span>',
             '>Removed from your profile keywords:</span>': '>Tolte dalle parole chiave del tuo profilo:</span>',
             'title="Count it again">restore</button>': 'title="Contala di nuovo">ripristina</button>',
             '<label>Skill or word</label><input name="term" placeholder="e.g. kubernetes, allemand" required>': '<label>Competenza o parola</label><input name="term" '
                                                                                                                 'placeholder="p. es. archicad, tedesco" required>',
             'value="have">+ Add skill</button>': 'value="have">+ Aggiungi</button>',
             'value="avoid">⛔ Avoid</button>': 'value="avoid">⛔ Evita</button>',
             '<strong>CV languages</strong>': '<strong>Lingue del CV</strong>',
             "A job's CV and cover letter use the posting's language when your profile has a version in it; otherwise the original.": "Il CV e la lettera di un'offerta "
                                                                                                                                      "sono nella lingua dell'annuncio "
                                                                                                                                      'quando il tuo profilo esiste in '
                                                                                                                                      'quella lingua; altrimenti nella '
                                                                                                                                      "lingua d'origine.",
             '{{ lang | upper }} · {{ state }}': '{{ lang | upper }} · {{ state | tr }}',
             'CV for a role</h2>': 'CV per un tipo di posto</h2>',
             '<p class="muted">No candidate profile yet.</p>': '<p class="muted">Ancora nessun profilo.</p>',
             "A CV aimed at a type of job rather than one posting: it leads with your skills that matter for the role (the role's usual requirements, plus what the jobs already found for it ask for most) and orders your experience for it. Nothing is invented.": 'Un '
                                                                                                                                                                                                                                                                      'CV '
                                                                                                                                                                                                                                                                      'per '
                                                                                                                                                                                                                                                                      'un '
                                                                                                                                                                                                                                                                      'tipo '
                                                                                                                                                                                                                                                                      'di '
                                                                                                                                                                                                                                                                      'posto '
                                                                                                                                                                                                                                                                      'anziché '
                                                                                                                                                                                                                                                                      'per '
                                                                                                                                                                                                                                                                      'un '
                                                                                                                                                                                                                                                                      'annuncio: '
                                                                                                                                                                                                                                                                      'mette '
                                                                                                                                                                                                                                                                      'in '
                                                                                                                                                                                                                                                                      'evidenza '
                                                                                                                                                                                                                                                                      'le '
                                                                                                                                                                                                                                                                      'tue '
                                                                                                                                                                                                                                                                      'competenze '
                                                                                                                                                                                                                                                                      'che '
                                                                                                                                                                                                                                                                      'contano '
                                                                                                                                                                                                                                                                      'per '
                                                                                                                                                                                                                                                                      'quel '
                                                                                                                                                                                                                                                                      'posto '
                                                                                                                                                                                                                                                                      '(i '
                                                                                                                                                                                                                                                                      'requisiti '
                                                                                                                                                                                                                                                                      'abituali, '
                                                                                                                                                                                                                                                                      'più '
                                                                                                                                                                                                                                                                      'ciò '
                                                                                                                                                                                                                                                                      'che '
                                                                                                                                                                                                                                                                      'chiedono '
                                                                                                                                                                                                                                                                      'di '
                                                                                                                                                                                                                                                                      'più '
                                                                                                                                                                                                                                                                      'le '
                                                                                                                                                                                                                                                                      'offerte '
                                                                                                                                                                                                                                                                      'già '
                                                                                                                                                                                                                                                                      'trovate) '
                                                                                                                                                                                                                                                                      'e '
                                                                                                                                                                                                                                                                      'ordina '
                                                                                                                                                                                                                                                                      'la '
                                                                                                                                                                                                                                                                      'tua '
                                                                                                                                                                                                                                                                      'esperienza '
                                                                                                                                                                                                                                                                      'di '
                                                                                                                                                                                                                                                                      'conseguenza. '
                                                                                                                                                                                                                                                                      'Niente '
                                                                                                                                                                                                                                                                      'è '
                                                                                                                                                                                                                                                                      'inventato.',
             '<label>Role</label>': '<label>Posto</label>',
             '<button type="submit">Generate</button>': '<button type="submit">Genera</button>',
             'Open CV for {{ role_built.label }} (PDF) ↗': 'Apri il CV per {{ role_built.label }} (PDF) ↗',
             'Often asked for this role, not in your profile (not added):': 'Spesso richiesto per questo posto, assente dal tuo profilo (non aggiunto):',
             'CV from keywords</h2>': 'CV da parole chiave</h2>',
             'No candidate profile yet (data/profile.json).': 'Ancora nessun profilo (data/profile.json).',
             "Type the keywords you want the CV to put forward (comma or one per line), for example the requirements of a posting. Keywords your profile already mentions get a <b>Key skills</b> section and move the matching bullets to the top of each role. Nothing is invented: keywords your CV doesn't support are listed below, not added.": 'Inserisci '
                                                                                                                                                                                                                                                                                                                                                      'le '
                                                                                                                                                                                                                                                                                                                                                      'parole '
                                                                                                                                                                                                                                                                                                                                                      'chiave '
                                                                                                                                                                                                                                                                                                                                                      'che '
                                                                                                                                                                                                                                                                                                                                                      'il '
                                                                                                                                                                                                                                                                                                                                                      'CV '
                                                                                                                                                                                                                                                                                                                                                      'deve '
                                                                                                                                                                                                                                                                                                                                                      'mettere '
                                                                                                                                                                                                                                                                                                                                                      'in '
                                                                                                                                                                                                                                                                                                                                                      'evidenza '
                                                                                                                                                                                                                                                                                                                                                      '(separate '
                                                                                                                                                                                                                                                                                                                                                      'da '
                                                                                                                                                                                                                                                                                                                                                      'virgole '
                                                                                                                                                                                                                                                                                                                                                      'o '
                                                                                                                                                                                                                                                                                                                                                      'una '
                                                                                                                                                                                                                                                                                                                                                      'per '
                                                                                                                                                                                                                                                                                                                                                      'riga), '
                                                                                                                                                                                                                                                                                                                                                      'per '
                                                                                                                                                                                                                                                                                                                                                      'esempio '
                                                                                                                                                                                                                                                                                                                                                      'i '
                                                                                                                                                                                                                                                                                                                                                      'requisiti '
                                                                                                                                                                                                                                                                                                                                                      'di '
                                                                                                                                                                                                                                                                                                                                                      'un '
                                                                                                                                                                                                                                                                                                                                                      'annuncio. '
                                                                                                                                                                                                                                                                                                                                                      'Quelle '
                                                                                                                                                                                                                                                                                                                                                      'che '
                                                                                                                                                                                                                                                                                                                                                      'il '
                                                                                                                                                                                                                                                                                                                                                      'tuo '
                                                                                                                                                                                                                                                                                                                                                      'profilo '
                                                                                                                                                                                                                                                                                                                                                      'menziona '
                                                                                                                                                                                                                                                                                                                                                      'già '
                                                                                                                                                                                                                                                                                                                                                      'formano '
                                                                                                                                                                                                                                                                                                                                                      'una '
                                                                                                                                                                                                                                                                                                                                                      'sezione '
                                                                                                                                                                                                                                                                                                                                                      '<b>Competenze '
                                                                                                                                                                                                                                                                                                                                                      'chiave</b> '
                                                                                                                                                                                                                                                                                                                                                      'e '
                                                                                                                                                                                                                                                                                                                                                      'fanno '
                                                                                                                                                                                                                                                                                                                                                      'salire '
                                                                                                                                                                                                                                                                                                                                                      'i '
                                                                                                                                                                                                                                                                                                                                                      'punti '
                                                                                                                                                                                                                                                                                                                                                      'corrispondenti '
                                                                                                                                                                                                                                                                                                                                                      'in '
                                                                                                                                                                                                                                                                                                                                                      'ogni '
                                                                                                                                                                                                                                                                                                                                                      'posto. '
                                                                                                                                                                                                                                                                                                                                                      'Niente '
                                                                                                                                                                                                                                                                                                                                                      'è '
                                                                                                                                                                                                                                                                                                                                                      'inventato: '
                                                                                                                                                                                                                                                                                                                                                      'le '
                                                                                                                                                                                                                                                                                                                                                      'parole '
                                                                                                                                                                                                                                                                                                                                                      'chiave '
                                                                                                                                                                                                                                                                                                                                                      'che '
                                                                                                                                                                                                                                                                                                                                                      'il '
                                                                                                                                                                                                                                                                                                                                                      'tuo '
                                                                                                                                                                                                                                                                                                                                                      'CV '
                                                                                                                                                                                                                                                                                                                                                      'non '
                                                                                                                                                                                                                                                                                                                                                      'giustifica '
                                                                                                                                                                                                                                                                                                                                                      'sono '
                                                                                                                                                                                                                                                                                                                                                      'elencate '
                                                                                                                                                                                                                                                                                                                                                      'qui '
                                                                                                                                                                                                                                                                                                                                                      'sotto, '
                                                                                                                                                                                                                                                                                                                                                      'senza '
                                                                                                                                                                                                                                                                                                                                                      'essere '
                                                                                                                                                                                                                                                                                                                                                      'aggiunte.',
             '<p><button type="submit">Generate CV</button></p>': '<p><button type="submit">Genera il CV</button></p>',
             '>Not in your CV, not added:</span>': '>Assente dal tuo CV, non aggiunto:</span>',
             '>Open CV (PDF) ↗</a>': '>Apri il CV (PDF) ↗</a>',
             'Often asked in your jobs</h2>': 'Spesso richiesto nelle tue offerte</h2>',
             'Skills that the {{ asked_of }} jobs found for you mention and that are not in your list. Do you have them? Saying so re-ranks the list at once. Nothing is added to your CV unless your profile mentions it.': 'Competenze '
                                                                                                                                                                                                                             'citate '
                                                                                                                                                                                                                             'dalle '
                                                                                                                                                                                                                             '{{ '
                                                                                                                                                                                                                             'asked_of '
                                                                                                                                                                                                                             '}} '
                                                                                                                                                                                                                             'offerte '
                                                                                                                                                                                                                             'trovate '
                                                                                                                                                                                                                             'per '
                                                                                                                                                                                                                             'te '
                                                                                                                                                                                                                             'e '
                                                                                                                                                                                                                             'assenti '
                                                                                                                                                                                                                             'dalla '
                                                                                                                                                                                                                             'tua '
                                                                                                                                                                                                                             'lista. '
                                                                                                                                                                                                                             'Le '
                                                                                                                                                                                                                             'hai? '
                                                                                                                                                                                                                             'Dirlo '
                                                                                                                                                                                                                             'riordina '
                                                                                                                                                                                                                             'subito '
                                                                                                                                                                                                                             'la '
                                                                                                                                                                                                                             'lista. '
                                                                                                                                                                                                                             'Niente '
                                                                                                                                                                                                                             'è '
                                                                                                                                                                                                                             'aggiunto '
                                                                                                                                                                                                                             'al '
                                                                                                                                                                                                                             'tuo '
                                                                                                                                                                                                                             'CV '
                                                                                                                                                                                                                             'se '
                                                                                                                                                                                                                             'il '
                                                                                                                                                                                                                             'tuo '
                                                                                                                                                                                                                             'profilo '
                                                                                                                                                                                                                             'non '
                                                                                                                                                                                                                             'lo '
                                                                                                                                                                                                                             'menziona.',
             "· {{ n }} job{{ 's' if n != 1 }}</span>": "· {{ n }} offert{{ 'e' if n != 1 else 'a' }}</span>",
             'title="I have this skill: count it from now on">+ I have it</button>': 'title="Ho questa competenza: contala da subito">+ Ce l\'ho</button>',
             'title="Push jobs that ask for this down the list">⛔ Avoid</button>': 'title="Fai scendere le offerte che la richiedono">⛔ Evita</button>',
             'title="Stop suggesting this word">not relevant</button>': 'title="Non proporre più questa parola">non pertinente</button>',
             'Profile check <span class="muted">': 'Controllo del profilo <span class="muted">',
             'Translate my profile →</a>': 'Traduci il mio profilo →</a>',
             '>Edit my profile</button>': '>Modifica il mio profilo</button>',
             'Write your profile in another language, next to the original:</span>': "Scrivi il tuo profilo in un'altra lingua, accanto all'originale:</span>",
             '<strong>Photo on your CV</strong>': '<strong>Foto sul tuo CV</strong>',
             '· most Swiss employers expect a portrait: recent, neutral background, like a passport photo but friendlier': '· la maggior parte dei datori di lavoro '
                                                                                                                           'svizzeri si aspetta un ritratto: recente, '
                                                                                                                           'sfondo neutro, come una fototessera ma più '
                                                                                                                           'sorridente',
             'That file is not a picture we can read. Use a JPEG or PNG of at most 8 MB.': "Questo file non è un'immagine leggibile. Usa un JPEG o un PNG di 8 MB al "
                                                                                           'massimo.',
             'alt="Your photo"': 'alt="La tua foto"',
             '{% if has_photo %}Replace the photo{% else %}Add the photo{% endif %}': '{% if has_photo %}Sostituisci la foto{% else %}Aggiungi la foto{% endif %}',
             'type="submit">Remove</button>': 'type="submit">Togli</button>',
             'It is placed at the top right of every CV made from now on. It stays in your workspace.': 'È posta in alto a destra su ogni CV generato da ora in poi. '
                                                                                                        'Resta nel tuo spazio.',
             '>CV and profile</a>': '>CV e profilo</a>',
             '>My CV versions</a>': '>Le mie versioni del CV</a>'},
 'settings.html': {'Saved. The next scan uses these settings{% if rescored %}; jobs already found were re-ranked{% endif %}.': 'Salvato. La prossima ricerca userà '
                                                                                                                               'queste impostazioni{% if rescored %}; le '
                                                                                                                               'offerte già trovate sono state '
                                                                                                                               'riordinate{% endif %}.',
                   'Search settings</h2>': 'Impostazioni della ricerca</h2>',
                   '<button type="submit">Save</button>': '<button type="submit">Salva</button>',
                   'Profile &amp; setup</h3>': 'Profilo e configurazione</h3>',
                   'Your profile is what CVs and letters are built from.': 'I tuoi CV e le tue lettere sono costruiti a partire dal tuo profilo.',
                   '>Edit my profile</button>': '>Modifica il mio profilo</button>',
                   '>Re-run the setup wizard (new CV / new target)</button>': ">Riavvia l'assistente (nuovo CV / nuovo obiettivo)</button>",
                   ' A new search has started with them: the results arrive on the Jobs page in a few minutes.': ' Una nuova ricerca è partita con queste impostazioni: '
                                                                                                                 'i risultati arrivano nella pagina Offerte tra qualche '
                                                                                                                 'minuto.',
                   '<h3 style="margin-top:0">Calendar</h3>': '<h3 style="margin-top:0">Calendario</h3>',
                   'Interviews, ORP deadlines, follow-up dates and the monthly hand-in of your proofs of job search, in the calendar of your phone or computer. Copy this address into your calendar app (“subscribe to a calendar” / “add by URL”). It updates by itself.': 'Colloqui, '
                                                                                                                                                                                                                                                                             'termini '
                                                                                                                                                                                                                                                                             "dell'URC, "
                                                                                                                                                                                                                                                                             'date '
                                                                                                                                                                                                                                                                             'dei '
                                                                                                                                                                                                                                                                             'solleciti '
                                                                                                                                                                                                                                                                             'e '
                                                                                                                                                                                                                                                                             'consegna '
                                                                                                                                                                                                                                                                             'mensile '
                                                                                                                                                                                                                                                                             'delle '
                                                                                                                                                                                                                                                                             'prove '
                                                                                                                                                                                                                                                                             'delle '
                                                                                                                                                                                                                                                                             'ricerche '
                                                                                                                                                                                                                                                                             'di '
                                                                                                                                                                                                                                                                             'lavoro, '
                                                                                                                                                                                                                                                                             'nel '
                                                                                                                                                                                                                                                                             'calendario '
                                                                                                                                                                                                                                                                             'del '
                                                                                                                                                                                                                                                                             'tuo '
                                                                                                                                                                                                                                                                             'telefono '
                                                                                                                                                                                                                                                                             'o '
                                                                                                                                                                                                                                                                             'computer. '
                                                                                                                                                                                                                                                                             'Copia '
                                                                                                                                                                                                                                                                             'questo '
                                                                                                                                                                                                                                                                             'indirizzo '
                                                                                                                                                                                                                                                                             'nella '
                                                                                                                                                                                                                                                                             'tua '
                                                                                                                                                                                                                                                                             'app '
                                                                                                                                                                                                                                                                             'di '
                                                                                                                                                                                                                                                                             'calendario '
                                                                                                                                                                                                                                                                             '(«abbonati '
                                                                                                                                                                                                                                                                             'a '
                                                                                                                                                                                                                                                                             'un '
                                                                                                                                                                                                                                                                             'calendario» '
                                                                                                                                                                                                                                                                             '/ '
                                                                                                                                                                                                                                                                             '«aggiungi '
                                                                                                                                                                                                                                                                             'tramite '
                                                                                                                                                                                                                                                                             'URL»). '
                                                                                                                                                                                                                                                                             'Si '
                                                                                                                                                                                                                                                                             'aggiorna '
                                                                                                                                                                                                                                                                             'da '
                                                                                                                                                                                                                                                                             'solo.',
                   'aria-label="Calendar address"': 'aria-label="Indirizzo del calendario"',
                   'Add to my calendar</a>': 'Aggiungi al mio calendario</a>',
                   "confirm('The current address will stop working. Continue?')": "confirm('Questo indirizzo non funzionerà più. Continuare?')",
                   'New address</button>': 'Nuovo indirizzo</button>',
                   'Anyone who has this address can read these dates (job titles and companies, nothing else). A new address makes the old one stop working.': 'Chiunque '
                                                                                                                                                               'abbia '
                                                                                                                                                               'questo '
                                                                                                                                                               'indirizzo '
                                                                                                                                                               'può '
                                                                                                                                                               'leggere '
                                                                                                                                                               'queste '
                                                                                                                                                               'date '
                                                                                                                                                               '(titoli '
                                                                                                                                                               'dei '
                                                                                                                                                               'posti e '
                                                                                                                                                               'aziende, '
                                                                                                                                                               "nient'altro). "
                                                                                                                                                               'Un nuovo '
                                                                                                                                                               'indirizzo '
                                                                                                                                                               'disattiva '
                                                                                                                                                               'quello '
                                                                                                                                                               'vecchio.'},
 '_settings_form.html': {'<label>Language of this site</label>': '<label>Lingua di questo sito</label>',
                         '("", "Automatic (your browser\'s)")': '("", "Automatica (quella del tuo browser)")',
                         '<label>Home town</label><input name="HOME_TOWN" value="{{ s.HOME_TOWN }}" placeholder="e.g. Genève, Lausanne, Pully">': '<label>Domicilio '
                                                                                                                                                  '(località)</label><input '
                                                                                                                                                  'name="HOME_TOWN" '
                                                                                                                                                  'value="{{ s.HOME_TOWN '
                                                                                                                                                  '}}" placeholder="p. '
                                                                                                                                                  'es. Lugano, '
                                                                                                                                                  'Bellinzona, Ginevra">',
                         'Used for the travel time to each job, and for the search area below.': 'Serve per il tempo di viaggio fino a ogni offerta e per la zona di '
                                                                                                 'ricerca qui sotto.',
                         '<label>Search radius (km)</label>': '<label>Raggio di ricerca (km)</label>',
                         'When you change the town or the radius, the towns and cantons to search are recalculated. 0 = keep the towns as typed.': 'Quando cambi la '
                                                                                                                                                   'località o il '
                                                                                                                                                   'raggio, le località '
                                                                                                                                                   'e i cantoni da '
                                                                                                                                                   'cercare vengono '
                                                                                                                                                   'ricalcolati. 0 = '
                                                                                                                                                   'tieni le località '
                                                                                                                                                   'inserite.',
                         '<label>Longest travel (minutes)</label>': '<label>Tragitto massimo (minuti)</label>',
                         'Jobs further by public transport are greyed out. 0 = no limit.': 'Le offerte più lontane con i trasporti pubblici sono in grigio. 0 = nessun '
                                                                                           'limite.',
                         '"Search terms", "Typed into the job boards, one per line."': '"Termini di ricerca", "Inseriti nei siti di lavoro, uno per riga."',
                         '"A job title must contain one of", "Whole words; a trailing * matches the start of a word (coordinat* = coordinateur, coordinatrice)."': '"Il '
                                                                                                                                                                   'titolo '
                                                                                                                                                                   'del '
                                                                                                                                                                   'posto '
                                                                                                                                                                   'deve '
                                                                                                                                                                   'contenere '
                                                                                                                                                                   'uno '
                                                                                                                                                                   'di", '
                                                                                                                                                                   '"Parole '
                                                                                                                                                                   'intere; '
                                                                                                                                                                   'un * '
                                                                                                                                                                   'finale '
                                                                                                                                                                   'corrisponde '
                                                                                                                                                                   "all'inizio "
                                                                                                                                                                   'di '
                                                                                                                                                                   'una '
                                                                                                                                                                   'parola '
                                                                                                                                                                   '(coordinat* '
                                                                                                                                                                   '= '
                                                                                                                                                                   'coordinatore, '
                                                                                                                                                                   'coordinatrice)."',
                         '"Skip job titles containing"': '"Ignora i titoli che contengono"',
                         '"Never show these companies or agencies", "One per line: a word or the name as it appears on the job."': '"Non mostrare mai queste aziende o '
                                                                                                                                   'agenzie", "Una per riga: una parola '
                                                                                                                                   'o il nome come appare '
                                                                                                                                   'nell\'offerta."',
                         '<label>Work rate wanted, from (%)</label>': '<label>Grado di occupazione desiderato, da (%)</label>',
                         '<label>to (%)</label>': '<label>a (%)</label>',
                         'A job whose title states a rate outside this range is skipped (0 to 100 = any).': "Un'offerta il cui titolo indica un grado fuori da questo "
                                                                                                            'intervallo è ignorata (da 0 a 100 = tutti).',
                         '<label>ORP target (applications per month)</label>': '<label>Obiettivo URC (candidature al mese)</label>',
                         '"Job location must mention one of", "Towns within your commute, their cantons and regions."': '"Il luogo del posto deve menzionare uno di", '
                                                                                                                        '"Località alla tua portata, i loro cantoni e '
                                                                                                                        'regioni."',
                         '"Regions for the job boards"': '"Regioni per i siti di lavoro"',
                         '"Cantons (Job-Room)", "Two-letter codes: VD, GE…"': '"Cantoni (Job-Room)", "Sigle di due lettere: TI, GR…"',
                         '"Your skills (ranking)", "A job scores higher the more of these it mentions. Refined by your clicks on job pages."': '"Le tue competenze '
                                                                                                                                               '(classifica)", "Più '
                                                                                                                                               "un'offerta ne menziona, "
                                                                                                                                               'più alto è il suo '
                                                                                                                                               'punteggio. Affinate dai '
                                                                                                                                               'tuoi clic sulle '
                                                                                                                                               'offerte."',
                         '"Posting languages"': '"Lingue degli annunci"',
                         '"Sources", "ats, jobup, jobroom, remote, adzuna, careerjet, jooble, email"': '"Fonti", "ats, jobup, jobroom, remote, adzuna, careerjet, '
                                                                                                       'jooble, email"',
                         '> Include remote jobs (Switzerland / Europe)</label>': '> Includi il telelavoro (Svizzera / Europa)</label>',
                         '<label>Scan every (hours)</label>': '<label>Cerca ogni (ore)</label>'},
 'onboarding.html': {'("import", "1 · Import"), ("review", "2 · Your profile"), ("target", "3 · What you\'re looking for"), ("confirm", "4 · Your search")': '("import", '
                                                                                                                                                             '"1 · '
                                                                                                                                                             'Importa"), '
                                                                                                                                                             '("review", '
                                                                                                                                                             '"2 · Il '
                                                                                                                                                             'tuo '
                                                                                                                                                             'profilo"), '
                                                                                                                                                             '("target", '
                                                                                                                                                             '"3 · Cosa '
                                                                                                                                                             'cerchi"), '
                                                                                                                                                             '("confirm", '
                                                                                                                                                             '"4 · La '
                                                                                                                                                             'tua '
                                                                                                                                                             'ricerca")',
                     "Welcome! Let's set up your job search</h2>": 'Benvenuto! Prepariamo la tua ricerca di lavoro</h2>',
                     "Upload what you have: your CV, your LinkedIn profile, or both. We read them here, inside your own private space, to prefill your profile. You'll review everything in the next step. Nothing is sent anywhere.": 'Importa '
                                                                                                                                                                                                                                       'ciò '
                                                                                                                                                                                                                                       'che '
                                                                                                                                                                                                                                       'hai: '
                                                                                                                                                                                                                                       'il '
                                                                                                                                                                                                                                       'tuo '
                                                                                                                                                                                                                                       'CV, '
                                                                                                                                                                                                                                       'il '
                                                                                                                                                                                                                                       'tuo '
                                                                                                                                                                                                                                       'profilo '
                                                                                                                                                                                                                                       'LinkedIn, '
                                                                                                                                                                                                                                       'o '
                                                                                                                                                                                                                                       'entrambi. '
                                                                                                                                                                                                                                       'Vengono '
                                                                                                                                                                                                                                       'letti '
                                                                                                                                                                                                                                       'qui, '
                                                                                                                                                                                                                                       'nel '
                                                                                                                                                                                                                                       'tuo '
                                                                                                                                                                                                                                       'spazio '
                                                                                                                                                                                                                                       'privato, '
                                                                                                                                                                                                                                       'per '
                                                                                                                                                                                                                                       'precompilare '
                                                                                                                                                                                                                                       'il '
                                                                                                                                                                                                                                       'tuo '
                                                                                                                                                                                                                                       'profilo. '
                                                                                                                                                                                                                                       'Verificherai '
                                                                                                                                                                                                                                       'tutto '
                                                                                                                                                                                                                                       'al '
                                                                                                                                                                                                                                       'passo '
                                                                                                                                                                                                                                       'successivo. '
                                                                                                                                                                                                                                       'Niente '
                                                                                                                                                                                                                                       'è '
                                                                                                                                                                                                                                       'inviato '
                                                                                                                                                                                                                                       'altrove.',
                     '<label>Your CV (PDF, Word .docx or .txt)</label>': '<label>Il tuo CV (PDF, Word .docx o .txt)</label>',
                     '<label>LinkedIn profile PDF</label>': '<label>Profilo LinkedIn in PDF</label>',
                     'On your LinkedIn profile page: <b>More</b> (or <b>Resources</b>) → <b>Save to PDF</b>.': 'Sulla tua pagina del profilo LinkedIn: <b>Altro</b> (o '
                                                                                                               '<b>Risorse</b>) → <b>Salva come PDF</b>.',
                     '<label>LinkedIn data export (.zip, complete or partial, or single .csv files from it)</label>': '<label>Esportazione dei dati LinkedIn (.zip, '
                                                                                                                      'completa o parziale, o singoli file .csv)</label>',
                     '<summary>How to get the export</summary>': "<summary>Come ottenere l'esportazione</summary>",
                     'LinkedIn → <b>Me</b> → <b>Settings &amp; Privacy</b> → <b>Data privacy</b> → <b>Get a copy of your data</b> → choose <i>Profile, Positions, Education, Skills, Languages, Certifications</i> → <b>Request archive</b>. LinkedIn emails you a link within minutes; upload the .zip here. It is the most complete source (all positions with dates, skills, languages). A partial export works too: what it holds is used and you fill in the rest.': 'LinkedIn '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '→ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '<b>Tu</b> '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '→ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '<b>Impostazioni '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'e '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'privacy</b> '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '→ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '<b>Privacy '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'dei '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'dati</b> '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '→ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '<b>Ottieni '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'una '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'copia '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'dei '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'tuoi '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'dati</b> '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '→ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'scegli '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '<i>Profilo, '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'Posizioni, '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'Formazione, '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'Competenze, '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'Lingue, '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'Certificazioni</i> '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '→ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '<b>Richiedi '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'archivio</b>. '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'LinkedIn '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'ti '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'invia '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'un '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'link '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'per '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'e-mail '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'in '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'pochi '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'minuti; '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'importa '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'qui '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'il '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'file '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '.zip. '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'È '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'la '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'fonte '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'più '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'completa '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          '(tutti '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'i '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'posti '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'con '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'date, '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'competenze, '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'lingue). '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'Funziona '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'anche '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          "un'esportazione "
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'parziale: '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'ciò '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'che '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'contiene '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'viene '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'usato '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'e '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'tu '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'completi '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'il '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          'resto.',
                     '>Read my files →</button>': '>Leggi i miei file →</button>',
                     '>I have no file: start from an empty profile</button>': '>Non ho file: parti da un profilo vuoto</button>',
                     '<h2 style="margin-top:0">Your profile</h2>': '<h2 style="margin-top:0">Il tuo profilo</h2>',
                     "This is what your CVs and cover letters are built from. Check and correct it: the import is automatic and can misread a layout. Only what's written here is ever used; nothing is invented.": 'È '
                                                                                                                                                                                                                    'da '
                                                                                                                                                                                                                    'qui '
                                                                                                                                                                                                                    'che '
                                                                                                                                                                                                                    'vengono '
                                                                                                                                                                                                                    'costruiti '
                                                                                                                                                                                                                    'i '
                                                                                                                                                                                                                    'tuoi '
                                                                                                                                                                                                                    'CV '
                                                                                                                                                                                                                    'e '
                                                                                                                                                                                                                    'le '
                                                                                                                                                                                                                    'tue '
                                                                                                                                                                                                                    'lettere. '
                                                                                                                                                                                                                    'Verifica '
                                                                                                                                                                                                                    'e '
                                                                                                                                                                                                                    'correggi: '
                                                                                                                                                                                                                    "l'importazione "
                                                                                                                                                                                                                    'è '
                                                                                                                                                                                                                    'automatica '
                                                                                                                                                                                                                    'e '
                                                                                                                                                                                                                    'può '
                                                                                                                                                                                                                    'leggere '
                                                                                                                                                                                                                    'male '
                                                                                                                                                                                                                    "un'impaginazione. "
                                                                                                                                                                                                                    'Viene '
                                                                                                                                                                                                                    'usato '
                                                                                                                                                                                                                    'solo '
                                                                                                                                                                                                                    'ciò '
                                                                                                                                                                                                                    'che '
                                                                                                                                                                                                                    'è '
                                                                                                                                                                                                                    'scritto '
                                                                                                                                                                                                                    'qui; '
                                                                                                                                                                                                                    'niente '
                                                                                                                                                                                                                    'è '
                                                                                                                                                                                                                    'inventato.',
                     '{% if sources %}Read from: {{ sources | join(", ") }}.{% endif %}': '{% if sources %}Letto da: {{ sources | join(", ") }}.{% endif %}',
                     '<label>Full name</label>': '<label>Nome completo</label>',
                     '<label>Headline (the line under your name)</label>': '<label>Titolo (la riga sotto il tuo nome)</label>',
                     '<label>Email</label>': '<label>E-mail</label>',
                     '<label>Phone</label>': '<label>Telefono</label>',
                     '<label>Location (town, country)</label>': '<label>Luogo (località, paese)</label>',
                     '<label>Summary (a few sentences about you)</label>': '<label>Riassunto (qualche frase su di te)</label>',
                     '<h3 style="margin-top:0">Skills</h3>': '<h3 style="margin-top:0">Competenze</h3>',
                     'Keywords used to rank jobs for you. Found in your files; add or remove freely (comma-separated).': 'Parole chiave che servono a classificare le '
                                                                                                                         'offerte per te. Trovate nei tuoi file; '
                                                                                                                         'aggiungi o togli liberamente (separate da '
                                                                                                                         'virgole).',
                     '<label>Areas of expertise (shown on your CV, one per line)</label>': '<label>Aree di competenza (mostrate sul tuo CV, una per riga)</label>',
                     '<label>Languages (one per line: language, level)</label>': '<label>Lingue (una per riga: lingua, livello)</label>',
                     'Levels: native, fluent, professional, intermediate, basic.': 'Livelli (da scrivere in inglese): native, fluent, professional, intermediate, basic.',
                     '<h3 style="margin-top:0">Experience</h3>': '<h3 style="margin-top:0">Esperienza</h3>',
                     'Most recent first. One achievement or task per line.': 'La più recente per prima. Un risultato o un compito per riga.',
                     '<label>Job title</label>': '<label>Titolo del posto</label>',
                     '<label>Employer</label>': '<label>Datore di lavoro</label>',
                     '<label>Place</label>': '<label>Luogo</label>',
                     '<label>Dates</label>': '<label>Date</label>',
                     '<label>What you did / achieved</label>': '<label>Cosa hai fatto / realizzato</label>',
                     'formnovalidate>Remove this job</button>': 'formnovalidate>Togli questo posto</button>',
                     'formnovalidate>+ Add a job</button>': 'formnovalidate>+ Aggiungi un posto</button>',
                     'Education &amp; more</h3>': 'Formazione e altro</h3>',
                     '<label>Education (one per line)</label>': '<label>Formazione (una per riga)</label>',
                     '<label>Extra section title (e.g. CERTIFICATIONS)</label>': '<label>Titolo della sezione supplementare (p. es. CERTIFICAZIONI)</label>',
                     '<label>Extra section lines (one per line)</label>': '<label>Righe della sezione supplementare (una per riga)</label>',
                     'value="next">Save and continue →</button>': 'value="next">Salva e continua →</button>',
                     'formnovalidate>← Import other files</button>': 'formnovalidate>← Importa altri file</button>',
                     'What are you looking for?</h2>': 'Cosa cerchi?</h2>',
                     'Pre-selected from your experience. Pick up to 5 roles.': 'Preselezionato in base alla tua esperienza. Scegli fino a 5 posti.',
                     '<b>{{ fam }}</b>': '<b>{{ fam | tr }}</b>',
                     'style="font-size:11px">suggested</span>': 'style="font-size:11px">suggerito</span>',
                     '<label>Other job titles to search for (comma-separated, optional)</label>': '<label>Altri titoli di posto da cercare (separati da virgole, '
                                                                                                  'facoltativo)</label>',
                     '<label>Level</label>': '<label>Livello</label>',
                     "{{ 'selected' if k == t.seniority }}>{{ v }}</option>": "{{ 'selected' if k == t.seniority }}>{{ v | tr }}</option>",
                     '<h3 style="margin-top:0">Where</h3>': '<h3 style="margin-top:0">Dove</h3>',
                     '<label>Home town</label>': '<label>Domicilio (località)</label>',
                     '<label>Maximum commute (straight line)</label>': "<label>Distanza massima (in linea d'aria)</label>",
                     '> Also postings that only say "Switzerland"</label>': '> Anche gli annunci che indicano solo «Svizzera»</label>',
                     '> Remote jobs open to Switzerland / Europe</label>': "> Telelavoro aperto alla Svizzera / all'Europa</label>",
                     '<h3 style="margin-top:0">Posting languages</h3>': '<h3 style="margin-top:0">Lingue degli annunci</h3>',
                     'Only postings written in these languages are kept. Pre-selected from the languages you work in.': 'Vengono tenuti solo gli annunci scritti in '
                                                                                                                        'queste lingue. Preselezionato in base alle tue '
                                                                                                                        'lingue di lavoro.',
                     '[("fr", "French"), ("de", "German"), ("it", "Italian"), ("en", "English")]': '[("fr", "Francese"), ("de", "Tedesco"), ("it", "Italiano"), ("en", '
                                                                                                   '"Inglese")]',
                     '<label>Words to avoid (comma-separated: jobs mentioning them go down the list)</label>': '<label>Parole da evitare (separate da virgole: le '
                                                                                                               'offerte che le menzionano scendono nella lista)</label>',
                     'placeholder="e.g. night shifts, german"': 'placeholder="p. es. lavoro notturno, tedesco"',
                     'value="next">Build my search →</button>': 'value="next">Costruisci la mia ricerca →</button>',
                     'formnovalidate>← Back to profile</button>': 'formnovalidate>← Torna al profilo</button>',
                     'Your search, ready to go</h2>': 'La tua ricerca è pronta</h2>',
                     "Built from your profile and choices. It's fine as is; you can change any of it later under <b>Settings</b>.": 'Costruita a partire dal tuo profilo '
                                                                                                                                    'e dalle tue scelte. Va bene così '
                                                                                                                                    "com'è; potrai modificare tutto più "
                                                                                                                                    'tardi in <b>Impostazioni</b>.',
                     'A CV for each target role</h3>': 'Un CV per ogni posto cercato</h3>',
                     'Leads with your skills that matter for the role and orders your experience for it. Only facts from your profile are used.': 'Mette in evidenza le '
                                                                                                                                                  'tue competenze che '
                                                                                                                                                  'contano per il posto '
                                                                                                                                                  'e ordina la tua '
                                                                                                                                                  'esperienza di '
                                                                                                                                                  'conseguenza. Vengono '
                                                                                                                                                  'usati solo i fatti '
                                                                                                                                                  'del tuo profilo.',
                     '>open PDF ↗</a>': '>apri il PDF ↗</a>',
                     '>Often asked for this role, not in your profile:</span>': '>Spesso richiesto per questo posto, assente dal tuo profilo:</span>',
                     '<p><button type="submit">Start my job search →</button>': '<p><button type="submit">Avvia la mia ricerca di lavoro →</button>',
                     'formnovalidate>← Change my choices</button>': 'formnovalidate>← Modifica le mie scelte</button>'},
 'week.html': {'My week <span class="muted">· week {{ w.week }}</span>': 'La mia settimana <span class="muted">· settimana {{ w.week }}</span>',
               'new jobs in the last 7 days': 'nuove offerte negli ultimi 7 giorni',
               'applications this week': 'candidature questa settimana',
               'this month (ORP target)': 'questo mese (obiettivo URC)',
               'days left in the month': 'giorni rimasti nel mese',
               '🎯 Interviews in the next 7 days': '🎯 Colloqui nei prossimi 7 giorni',
               '📌 Assigned by the ORP, to apply': "📌 Assegnazioni dell'URC, da candidarsi",
               '★ The best new jobs of the week': '★ Le migliori nuove offerte della settimana',
               'score {{ j.score }}': 'punteggio {{ j.score }}',
               'Open the best new jobs →</a>': 'Apri le migliori nuove offerte →</a>',
               'Nothing new this week. Widen the search in <a href="/settings">Settings</a>: more towns, more job titles.': 'Niente di nuovo questa settimana. Allarga '
                                                                                                                            'la ricerca nelle <a '
                                                                                                                            'href="/settings">Impostazioni</a>: più '
                                                                                                                            'località, più titoli di posto.',
               '✉ No answer yet: time to follow up?': '✉ Ancora nessuna risposta: sollecitare?',
               'applied {{ j.days_waiting }} days ago': 'candidatura inviata {{ j.days_waiting }} giorni fa',
               '⏰ Follow-ups due this week': '⏰ Solleciti previsti questa settimana',
               '✓ Applied this week': '✓ Candidature di questa settimana',
               'No application recorded this week yet.': 'Nessuna candidatura registrata questa settimana per ora.',
               "{{ w.orp.missing }} more application{{ 's' if w.orp.missing != 1 }} to reach this month's target.": "Ancora {{ w.orp.missing }} candidatur{{ 'e' if "
                                                                                                                    "w.orp.missing != 1 else 'a' }} per raggiungere "
                                                                                                                    "l'obiettivo del mese.",
               '+ spontaneous application</a>': '+ candidatura spontanea</a>',
               'Want these dates in your phone\'s calendar? <a href="/settings#calendar">Add the calendar</a>.': 'Vuoi queste date nel calendario del tuo telefono? <a '
                                                                                                                 'href="/settings#calendar">Aggiungi il calendario</a>.',
               '<strong>🏅 My score</strong> <span class="muted">· level {{ g.level + 1 }}: {{ g.level_name | tr }}</span>': '<strong>🏅 Il mio punteggio</strong> <span '
                                                                                                                            'class="muted">· livello {{ g.level + 1 }}: '
                                                                                                                            '{{ g.level_name | tr }}</span>',
               '🏆 The league</a>': '🏆 La lega</a>',
               '<div class="l">points this week</div>': '<div class="l">punti questa settimana</div>',
               '<div class="l">points this month</div>': '<div class="l">punti questo mese</div>',
               '<div class="l">points in total</div>': '<div class="l">punti in totale</div>',
               'weeks in a row with an application': 'settimane di fila con una candidatura',
               '{{ g.to_next }} points to the next level.': 'Ancora {{ g.to_next }} punti al prossimo livello.',
               'No badge yet: the first one comes with your first application.': 'Ancora nessun badge: il primo arriva con la tua prima candidatura.',
               'Next badges:': 'Prossimi badge:',
               '>How points are counted</summary>': '>Come si contano i punti</summary>',
               'Application sent {{ pts.applied }} · interview {{ pts.interview }} · offer {{ pts.offer }} · follow-up sent {{ pts.followup }} · CV written for the job {{ pts.cv }} · letter written for the job {{ pts.letter }} · monthly target reached {{ pts.target }} · a refusal {{ pts.refusal }} (you tried) · a job shortlisted, or discarded with a reason {{ pts.sorted }} (at most 20 a week).': 'Candidatura '
                                                                                                                                                                                                                                                                                                                                                                                                               'inviata '
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.applied '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               'colloquio '
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.interview '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               'offerta '
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.offer '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               'sollecito '
                                                                                                                                                                                                                                                                                                                                                                                                               'inviato '
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.followup '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               'CV '
                                                                                                                                                                                                                                                                                                                                                                                                               'scritto '
                                                                                                                                                                                                                                                                                                                                                                                                               'per '
                                                                                                                                                                                                                                                                                                                                                                                                               "l'offerta "
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.cv '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               'lettera '
                                                                                                                                                                                                                                                                                                                                                                                                               'scritta '
                                                                                                                                                                                                                                                                                                                                                                                                               'per '
                                                                                                                                                                                                                                                                                                                                                                                                               "l'offerta "
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.letter '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               'obiettivo '
                                                                                                                                                                                                                                                                                                                                                                                                               'mensile '
                                                                                                                                                                                                                                                                                                                                                                                                               'raggiunto '
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.target '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               'un '
                                                                                                                                                                                                                                                                                                                                                                                                               'rifiuto '
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.refusal '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '(ci '
                                                                                                                                                                                                                                                                                                                                                                                                               'hai '
                                                                                                                                                                                                                                                                                                                                                                                                               'provato) '
                                                                                                                                                                                                                                                                                                                                                                                                               '· '
                                                                                                                                                                                                                                                                                                                                                                                                               "un'offerta "
                                                                                                                                                                                                                                                                                                                                                                                                               'tenuta, '
                                                                                                                                                                                                                                                                                                                                                                                                               'o '
                                                                                                                                                                                                                                                                                                                                                                                                               'scartata '
                                                                                                                                                                                                                                                                                                                                                                                                               'con '
                                                                                                                                                                                                                                                                                                                                                                                                               'un '
                                                                                                                                                                                                                                                                                                                                                                                                               'motivo '
                                                                                                                                                                                                                                                                                                                                                                                                               '{{ '
                                                                                                                                                                                                                                                                                                                                                                                                               'pts.sorted '
                                                                                                                                                                                                                                                                                                                                                                                                               '}} '
                                                                                                                                                                                                                                                                                                                                                                                                               '(al '
                                                                                                                                                                                                                                                                                                                                                                                                               'massimo '
                                                                                                                                                                                                                                                                                                                                                                                                               '20 '
                                                                                                                                                                                                                                                                                                                                                                                                               'a '
                                                                                                                                                                                                                                                                                                                                                                                                               'settimana).'},
 'translate.html': {'← back to CV</a>': '← torna al CV</a>',
                    'Saved: {{ saved }} of {{ total }} texts translated. CVs and letters for jobs posted in this language now use them.': 'Salvato: {{ saved }} testi '
                                                                                                                                          'tradotti su {{ total }}. I CV '
                                                                                                                                          'e le lettere per le offerte '
                                                                                                                                          'pubblicate in questa lingua '
                                                                                                                                          'ora li usano.',
                    'My profile {{ ("in " ~ names[lang]) | tr }}</h2>': 'Il mio profilo {{ ("in " ~ names[lang]) | tr }}</h2>',
                    'Your own text is on the left; write the translation on the right. Nothing is translated by a machine and nothing is sent anywhere: what you write here is what goes on your CV. A box left empty keeps the original text. Names, dates of birth and contact details stay as they are.': 'Il '
                                                                                                                                                                                                                                                                                                             'tuo '
                                                                                                                                                                                                                                                                                                             'testo '
                                                                                                                                                                                                                                                                                                             'è '
                                                                                                                                                                                                                                                                                                             'a '
                                                                                                                                                                                                                                                                                                             'sinistra; '
                                                                                                                                                                                                                                                                                                             'scrivi '
                                                                                                                                                                                                                                                                                                             'la '
                                                                                                                                                                                                                                                                                                             'traduzione '
                                                                                                                                                                                                                                                                                                             'a '
                                                                                                                                                                                                                                                                                                             'destra. '
                                                                                                                                                                                                                                                                                                             'Niente '
                                                                                                                                                                                                                                                                                                             'è '
                                                                                                                                                                                                                                                                                                             'tradotto '
                                                                                                                                                                                                                                                                                                             'da '
                                                                                                                                                                                                                                                                                                             'una '
                                                                                                                                                                                                                                                                                                             'macchina '
                                                                                                                                                                                                                                                                                                             'e '
                                                                                                                                                                                                                                                                                                             'niente '
                                                                                                                                                                                                                                                                                                             'è '
                                                                                                                                                                                                                                                                                                             'inviato '
                                                                                                                                                                                                                                                                                                             'altrove: '
                                                                                                                                                                                                                                                                                                             'ciò '
                                                                                                                                                                                                                                                                                                             'che '
                                                                                                                                                                                                                                                                                                             'scrivi '
                                                                                                                                                                                                                                                                                                             'qui '
                                                                                                                                                                                                                                                                                                             'è '
                                                                                                                                                                                                                                                                                                             'ciò '
                                                                                                                                                                                                                                                                                                             'che '
                                                                                                                                                                                                                                                                                                             'compare '
                                                                                                                                                                                                                                                                                                             'sul '
                                                                                                                                                                                                                                                                                                             'tuo '
                                                                                                                                                                                                                                                                                                             'CV. '
                                                                                                                                                                                                                                                                                                             'Una '
                                                                                                                                                                                                                                                                                                             'casella '
                                                                                                                                                                                                                                                                                                             'lasciata '
                                                                                                                                                                                                                                                                                                             'vuota '
                                                                                                                                                                                                                                                                                                             'mantiene '
                                                                                                                                                                                                                                                                                                             'il '
                                                                                                                                                                                                                                                                                                             'testo '
                                                                                                                                                                                                                                                                                                             'originale. '
                                                                                                                                                                                                                                                                                                             'I '
                                                                                                                                                                                                                                                                                                             'nomi '
                                                                                                                                                                                                                                                                                                             'e '
                                                                                                                                                                                                                                                                                                             'i '
                                                                                                                                                                                                                                                                                                             'recapiti '
                                                                                                                                                                                                                                                                                                             'restano '
                                                                                                                                                                                                                                                                                                             'come '
                                                                                                                                                                                                                                                                                                             'sono.',
                    'Save the translation</button>': 'Salva la traduzione</button>'},
 'versions.html': {'>CV and profile</a>': '>CV e profilo</a>',
                   '>My CV versions</a>': '>Le mie versioni del CV</a>',
                   '<div class="banner">Saved.</div>': '<div class="banner">Salvato.</div>',
                   "Not saved: give it a name that isn't used yet (at most {{ limit }} versions).": 'Non salvato: dai un nome non ancora usato (al massimo {{ limit }} '
                                                                                                    'versioni).',
                   '<h2 style="margin-top:0">My CV versions</h2>': '<h2 style="margin-top:0">Le mie versioni del CV</h2>',
                   'CVs you wrote once and keep under a name, for example one per kind of job. On a job page you choose which one to start from, change what you want, and get the PDF. The ★ default is the one offered first for every new job.': 'CV '
                                                                                                                                                                                                                                                    'scritti '
                                                                                                                                                                                                                                                    'una '
                                                                                                                                                                                                                                                    'volta '
                                                                                                                                                                                                                                                    'e '
                                                                                                                                                                                                                                                    'conservati '
                                                                                                                                                                                                                                                    'con '
                                                                                                                                                                                                                                                    'un '
                                                                                                                                                                                                                                                    'nome, '
                                                                                                                                                                                                                                                    'per '
                                                                                                                                                                                                                                                    'esempio '
                                                                                                                                                                                                                                                    'uno '
                                                                                                                                                                                                                                                    'per '
                                                                                                                                                                                                                                                    'tipo '
                                                                                                                                                                                                                                                    'di '
                                                                                                                                                                                                                                                    'posto. '
                                                                                                                                                                                                                                                    'Nella '
                                                                                                                                                                                                                                                    'pagina '
                                                                                                                                                                                                                                                    'di '
                                                                                                                                                                                                                                                    "un'offerta "
                                                                                                                                                                                                                                                    'scegli '
                                                                                                                                                                                                                                                    'da '
                                                                                                                                                                                                                                                    'quale '
                                                                                                                                                                                                                                                    'partire, '
                                                                                                                                                                                                                                                    'modifichi '
                                                                                                                                                                                                                                                    'ciò '
                                                                                                                                                                                                                                                    'che '
                                                                                                                                                                                                                                                    'vuoi '
                                                                                                                                                                                                                                                    'e '
                                                                                                                                                                                                                                                    'ottieni '
                                                                                                                                                                                                                                                    'il '
                                                                                                                                                                                                                                                    'PDF. '
                                                                                                                                                                                                                                                    'La '
                                                                                                                                                                                                                                                    'versione '
                                                                                                                                                                                                                                                    '★ '
                                                                                                                                                                                                                                                    'predefinita '
                                                                                                                                                                                                                                                    'è '
                                                                                                                                                                                                                                                    'quella '
                                                                                                                                                                                                                                                    'proposta '
                                                                                                                                                                                                                                                    'per '
                                                                                                                                                                                                                                                    'prima '
                                                                                                                                                                                                                                                    'per '
                                                                                                                                                                                                                                                    'ogni '
                                                                                                                                                                                                                                                    'nuova '
                                                                                                                                                                                                                                                    'offerta.',
                   '<p class="muted">No candidate profile yet.</p>': '<p class="muted">Ancora nessun profilo.</p>',
                   '<label>Name of a new version</label><input name="name" maxlength="60" required placeholder="e.g. Dessinatrice, Interior design">': '<label>Nome di '
                                                                                                                                                       'una nuova '
                                                                                                                                                       'versione</label><input '
                                                                                                                                                       'name="name" '
                                                                                                                                                       'maxlength="60" '
                                                                                                                                                       'required '
                                                                                                                                                       'placeholder="p. '
                                                                                                                                                       'es. '
                                                                                                                                                       'Disegnatrice, '
                                                                                                                                                       'Architettura '
                                                                                                                                                       'd\'interni">',
                   '+ New version from my profile</button>': '+ Nuova versione dal mio profilo</button>',
                   '<label>Name{% if v.is_default %} · ★ default{% endif %}</label>': '<label>Nome{% if v.is_default %} · ★ predefinita{% endif %}</label>',
                   'class="muted">changed {{ v.updated_at[:10] }}</div>': 'class="muted">modificata il {{ v.updated_at[:10] }}</div>',
                   '>Text of this version</summary>': '>Testo di questa versione</summary>',
                   'A line starting with ## is a section title, ### a job (the next line is its dates), - a point.': 'Una riga che inizia con ## è un titolo di sezione, '
                                                                                                                     '### un impiego (la riga seguente indica le date), '
                                                                                                                     '- un punto.',
                   'value="save">Save</button>': 'value="save">Salva</button>',
                   '>Open the PDF ↗</a>': '>Apri il PDF ↗</a>',
                   'value="undefault">No longer the default</button>': 'value="undefault">Non più predefinita</button>',
                   'value="default">★ Make it the default</button>': 'value="default">★ Rendi predefinita</button>',
                   '">Delete</button>': '">Elimina</button>',
                   'No version yet. Create one above, or use <b>Save as a version</b> under the CV of a job.': 'Ancora nessuna versione. Creane una qui sopra, o usa '
                                                                                                               "<b>Salva come versione</b> sotto il CV di un'offerta.",
                   "{company}, {title}, {location} and {date} are replaced by the job's when you use this letter.": '{company}, {title}, {location} e {date} sono '
                                                                                                                    "sostituiti da quelli dell'offerta quando usi questa "
                                                                                                                    'lettera.',
                   "confirm('Delete this version? What was already written for jobs is kept.')": "confirm('Eliminare questa versione? Ciò che è già stato scritto per le "
                                                                                                 "offerte resta.')",
                   '<h2 style="margin-top:0">My letters</h2>': '<h2 style="margin-top:0">Le mie lettere</h2>',
                   'Cover letters kept under a name, for example one per kind of employer. On a job page you choose which one to start from: the company, the job title, the place and the date are filled in for that job, and you can still change the text.': 'Lettere '
                                                                                                                                                                                                                                                                 'di '
                                                                                                                                                                                                                                                                 'motivazione '
                                                                                                                                                                                                                                                                 'conservate '
                                                                                                                                                                                                                                                                 'con '
                                                                                                                                                                                                                                                                 'un '
                                                                                                                                                                                                                                                                 'nome, '
                                                                                                                                                                                                                                                                 'per '
                                                                                                                                                                                                                                                                 'esempio '
                                                                                                                                                                                                                                                                 'una '
                                                                                                                                                                                                                                                                 'per '
                                                                                                                                                                                                                                                                 'tipo '
                                                                                                                                                                                                                                                                 'di '
                                                                                                                                                                                                                                                                 'datore '
                                                                                                                                                                                                                                                                 'di '
                                                                                                                                                                                                                                                                 'lavoro. '
                                                                                                                                                                                                                                                                 'Nella '
                                                                                                                                                                                                                                                                 'pagina '
                                                                                                                                                                                                                                                                 'di '
                                                                                                                                                                                                                                                                 "un'offerta "
                                                                                                                                                                                                                                                                 'scegli '
                                                                                                                                                                                                                                                                 'da '
                                                                                                                                                                                                                                                                 'quale '
                                                                                                                                                                                                                                                                 'partire: '
                                                                                                                                                                                                                                                                 "l'azienda, "
                                                                                                                                                                                                                                                                 'il '
                                                                                                                                                                                                                                                                 'titolo '
                                                                                                                                                                                                                                                                 'del '
                                                                                                                                                                                                                                                                 'posto, '
                                                                                                                                                                                                                                                                 'il '
                                                                                                                                                                                                                                                                 'luogo '
                                                                                                                                                                                                                                                                 'e '
                                                                                                                                                                                                                                                                 'la '
                                                                                                                                                                                                                                                                 'data '
                                                                                                                                                                                                                                                                 'sono '
                                                                                                                                                                                                                                                                 'inseriti '
                                                                                                                                                                                                                                                                 'per '
                                                                                                                                                                                                                                                                 "quell'offerta, "
                                                                                                                                                                                                                                                                 'e '
                                                                                                                                                                                                                                                                 'puoi '
                                                                                                                                                                                                                                                                 'ancora '
                                                                                                                                                                                                                                                                 'modificare '
                                                                                                                                                                                                                                                                 'il '
                                                                                                                                                                                                                                                                 'testo.',
                   '<label>Name of a new letter</label><input name="name" maxlength="60" required placeholder="e.g. Architecture office, Spontaneous">': '<label>Nome di '
                                                                                                                                                         'una nuova '
                                                                                                                                                         'lettera</label><input '
                                                                                                                                                         'name="name" '
                                                                                                                                                         'maxlength="60" '
                                                                                                                                                         'required '
                                                                                                                                                         'placeholder="p. '
                                                                                                                                                         'es. Studio di '
                                                                                                                                                         'architettura, '
                                                                                                                                                         'Spontanea">',
                   '+ New letter from my profile</button>': '+ Nuova lettera dal mio profilo</button>',
                   'No letter kept yet. Create one above, or use <b>Save as a letter version</b> under the letter of a job.': 'Ancora nessuna lettera conservata. Creane '
                                                                                                                              'una qui sopra, o usa <b>Salva come '
                                                                                                                              'modello di lettera</b> sotto la lettera '
                                                                                                                              "di un'offerta."},
 'improve.html': {'Improve <span class="muted">· what the {{ a.total }} jobs found for you ask for</span>': 'Migliorare <span class="muted">· cosa chiedono le {{ '
                                                                                                            'a.total }} offerte trovate per te</span>',
                  'aria-label="Kind of job"><option value="">All kinds of job ({{ a.all }})</option>': 'aria-label="Tipo di posto"><option value="">Tutti i tipi di '
                                                                                                       'posto ({{ a.all }})</option>',
                  'Choose a kind of job to see what that one asks for.': 'Scegli un tipo di posto per vedere cosa chiede.',
                  'No job to read yet. Come back after the first scan.': 'Ancora nessuna offerta da analizzare. Torna dopo la prima ricerca.',
                  'of the skills asked, you have on average': 'delle competenze richieste, le hai in media',
                  'jobs where you have every skill asked': 'offerte in cui hai tutte le competenze richieste',
                  'skills asked that are not in your list': 'competenze richieste assenti dalla tua lista',
                  '<div class="l">profile check</div>': '<div class="l">controllo del profilo</div>',
                  '<strong>⚡ Closest wins</strong> <span class="muted">· one skill away from a full match</span>': '<strong>⚡ I traguardi più vicini</strong> <span '
                                                                                                                   'class="muted">· a una competenza dalla '
                                                                                                                   'corrispondenza completa</span>',
                  'In these jobs it is the only skill you miss. Learning it, or adding it if you already have it, completes the match.': "In queste offerte è l'unica "
                                                                                                                                         'competenza che ti manca. '
                                                                                                                                         'Impararla, o aggiungerla se ce '
                                                                                                                                         "l'hai già, completa la "
                                                                                                                                         'corrispondenza.',
                  "· {{ m.only }} job{{ 's' if m.only != 1 }}</span>": "· {{ m.only }} offert{{ 'e' if m.only != 1 else 'a' }}</span>",
                  '<strong>📚 Skills you miss most</strong> <span class="muted">· what to study first</span>': '<strong>📚 Le competenze che ti mancano di più</strong> '
                                                                                                              '<span class="muted">· cosa studiare per primo</span>',
                  'Counted in the jobs still in your lists. “Chosen” = in jobs you shortlisted or applied to: those weigh more. Do you already have one? Say so and every job is re-ranked.': 'Contate '
                                                                                                                                                                                              'nelle '
                                                                                                                                                                                              'offerte '
                                                                                                                                                                                              'ancora '
                                                                                                                                                                                              'nelle '
                                                                                                                                                                                              'tue '
                                                                                                                                                                                              'liste. '
                                                                                                                                                                                              '«Scelte» '
                                                                                                                                                                                              '= '
                                                                                                                                                                                              'nelle '
                                                                                                                                                                                              'offerte '
                                                                                                                                                                                              'che '
                                                                                                                                                                                              'hai '
                                                                                                                                                                                              'tenuto '
                                                                                                                                                                                              'o '
                                                                                                                                                                                              'a '
                                                                                                                                                                                              'cui '
                                                                                                                                                                                              'ti '
                                                                                                                                                                                              'sei '
                                                                                                                                                                                              'candidato: '
                                                                                                                                                                                              'pesano '
                                                                                                                                                                                              'di '
                                                                                                                                                                                              'più. '
                                                                                                                                                                                              'Ne '
                                                                                                                                                                                              'hai '
                                                                                                                                                                                              'già '
                                                                                                                                                                                              'una? '
                                                                                                                                                                                              'Dillo '
                                                                                                                                                                                              'e '
                                                                                                                                                                                              'tutte '
                                                                                                                                                                                              'le '
                                                                                                                                                                                              'offerte '
                                                                                                                                                                                              'vengono '
                                                                                                                                                                                              'riordinate.',
                  '<tr><th>Skill</th><th>Jobs asking</th><th>Chosen</th><th>Mostly for</th><th>For example</th><th></th></tr>': '<tr><th>Competenza</th><th>Offerte che '
                                                                                                                                'la '
                                                                                                                                'chiedono</th><th>Scelte</th><th>Soprattutto '
                                                                                                                                'per</th><th>Per '
                                                                                                                                'esempio</th><th></th></tr>',
                  'title="I have this skill: count it from now on">+ I have it</button>': 'title="Ho questa competenza: contala da subito">+ Ce l\'ho</button>',
                  'title="Stop suggesting this word">not relevant</button>': 'title="Non proporre più questa parola">non pertinente</button>',
                  '>find a course ↗</a>': '>trova un corso ↗</a>',
                  'Registered with an ORP / RAV? Courses that close a gap asked by many jobs can be paid for as a labour-market measure: show this table to your adviser.': 'Iscritto '
                                                                                                                                                                            'a '
                                                                                                                                                                            'un '
                                                                                                                                                                            'URC? '
                                                                                                                                                                            'I '
                                                                                                                                                                            'corsi '
                                                                                                                                                                            'che '
                                                                                                                                                                            'colmano '
                                                                                                                                                                            'una '
                                                                                                                                                                            'lacuna '
                                                                                                                                                                            'richiesta '
                                                                                                                                                                            'da '
                                                                                                                                                                            'molte '
                                                                                                                                                                            'offerte '
                                                                                                                                                                            'possono '
                                                                                                                                                                            'essere '
                                                                                                                                                                            'finanziati '
                                                                                                                                                                            'come '
                                                                                                                                                                            'provvedimento '
                                                                                                                                                                            'del '
                                                                                                                                                                            'mercato '
                                                                                                                                                                            'del '
                                                                                                                                                                            'lavoro: '
                                                                                                                                                                            'mostra '
                                                                                                                                                                            'questa '
                                                                                                                                                                            'tabella '
                                                                                                                                                                            'al '
                                                                                                                                                                            'tuo '
                                                                                                                                                                            'consulente.',
                  'lists further training in Switzerland.': 'elenca le formazioni continue in Svizzera.',
                  'Nothing missing in these jobs: every known skill they name is in your list.': 'Non manca niente in queste offerte: tutte le competenze note che '
                                                                                                 'citano sono nella tua lista.',
                  '<strong>💪 Your skills that are asked most</strong> <span class="muted">· put these first on your CV and in your letters</span>': '<strong>💪 Le tue '
                                                                                                                                                    'competenze più '
                                                                                                                                                    'richieste</strong> '
                                                                                                                                                    '<span '
                                                                                                                                                    'class="muted">· '
                                                                                                                                                    'mettile per prime '
                                                                                                                                                    'nel CV e nelle '
                                                                                                                                                    'lettere</span>',
                  '<strong>🗣 Languages asked</strong>': '<strong>🗣 Lingue richieste</strong>',
                  '<tr><th>Language</th><th>Jobs</th><th>Level asked most</th><th></th></tr>': '<tr><th>Lingua</th><th>Offerte</th><th>Livello più '
                                                                                               'richiesto</th><th></th></tr>',
                  '<span class="chip have">✓ in your skills</span>': '<span class="chip have">✓ tra le tue competenze</span>',
                  '<span class="chip miss">not in your skills</span>': '<span class="chip miss">non tra le tue competenze</span>',
                  'A recognised certificate (DELF/DALF, Goethe/telc, Cambridge, CELI) proves a level better than a self-assessment.': 'Un certificato riconosciuto '
                                                                                                                                      '(DELF/DALF, Goethe/telc, '
                                                                                                                                      'Cambridge, CELI) prova un livello '
                                                                                                                                      "meglio di un'autovalutazione.",
                  '<strong>🎓 Experience and qualifications asked</strong>': '<strong>🎓 Esperienza e titoli richiesti</strong>',
                  'Years of experience, in the {{ a.years_n }} jobs that state it{% if my_years %} (you: about {{ my_years }}){% endif %}:': 'Anni di esperienza, nelle '
                                                                                                                                             '{{ a.years_n }} offerte '
                                                                                                                                             'che lo indicano{% if '
                                                                                                                                             'my_years %} (tu: circa {{ '
                                                                                                                                             'my_years }}){% endif %}:',
                  '<tr><th>Qualification named</th><th>Jobs</th></tr>': '<tr><th>Titolo citato</th><th>Offerte</th></tr>',
                  'A foreign diploma? Its Swiss equivalence (SEFRI / SBFI) is what employers look for: name it on your CV.': 'Un diploma estero? La sua equivalenza '
                                                                                                                             'svizzera (SEFRI) è ciò che guardano i '
                                                                                                                             'datori di lavoro: indicala nel CV.',
                  '<strong>🧭 By kind of job</strong> <span class="muted">· where you match best, and what each kind asks that you miss</span>': '<strong>🧭 Per tipo di '
                                                                                                                                                'posto</strong> <span '
                                                                                                                                                'class="muted">· dove '
                                                                                                                                                'corrispondi meglio, e '
                                                                                                                                                'cosa chiede ogni tipo '
                                                                                                                                                'che ti manca</span>',
                  '<tr><th>Kind of job</th><th>Jobs</th><th>Average match</th><th>Missing most</th></tr>': '<tr><th>Tipo di posto</th><th>Offerte</th><th>Punteggio '
                                                                                                           'medio</th><th>Manca di più</th></tr>',
                  '<strong>📋 Conditions named</strong>': '<strong>📋 Condizioni citate</strong>',
                  '<strong>📎 Documents asked</strong> <span class="muted">· have them ready as PDF</span>': '<strong>📎 Documenti richiesti</strong> <span '
                                                                                                            'class="muted">· tienili pronti in PDF</span>',
                  '<strong>➡ What to do with this</strong>': '<strong>➡ Cosa farne</strong>',
                  '<li>Tick the skills you already have: the list above gets shorter and your ranking better.</li>': '<li>Spunta le competenze che hai già: la lista qui '
                                                                                                                     'sopra si accorcia e la tua classifica '
                                                                                                                     'migliora.</li>',
                  '<li>Pick one or two of the skills asked most and plan a course or a certificate for them.</li>': '<li>Scegli una o due delle competenze più richieste '
                                                                                                                    'e pianifica un corso o un certificato.</li>',
                  '<li>Put your most asked skills at the top of your CV: <a href="/cv/versions">My CV versions</a>.</li>': '<li>Metti le tue competenze più richieste in '
                                                                                                                           'cima al CV: <a href="/cv/versions">Le mie '
                                                                                                                           'versioni del CV</a>.</li>',
                  '<li>Complete your profile: <a href="/cv#check">Profile check</a>. See why you discard jobs: <a href="/stats">Stats</a>.</li>': '<li>Completa il tuo '
                                                                                                                                                  'profilo: <a '
                                                                                                                                                  'href="/cv#check">Controllo '
                                                                                                                                                  'del profilo</a>. '
                                                                                                                                                  'Guarda perché scarti '
                                                                                                                                                  'le offerte: <a '
                                                                                                                                                  'href="/stats">Statistiche</a>.</li>'}}

STRINGS = {'CV': 'CV',
 'Cover letter': 'Lettera di motivazione',
 'Work certificates': 'Certificati di lavoro',
 'Diplomas and training certificates': 'Diplomi e attestati di formazione',
 'References (names and phone numbers)': 'Referenze (nomi e numeri di telefono)',
 'Copy of residence or work permit': 'Copia del permesso di dimora o di lavoro',
 'Criminal-record extract': 'Estratto del casellario giudiziale',
 'Debt-register extract': 'Estratto del registro delle esecuzioni',
 'Salary expectations': 'Pretese salariali',
 'Photo': 'Foto',
 'Contact details complete': 'Recapiti completi',
 'E-mail, phone number and town: recruiters call, and they check how far you live.': 'E-mail, telefono e località: i selezionatori telefonano, e guardano a che distanza '
                                                                                     'abiti.',
 'A job title under your name': 'Un titolo professionale sotto il tuo nome',
 'The title you are looking for, in the words job ads use.': 'Il posto che cerchi, con le parole degli annunci.',
 'A summary of 3 to 5 lines': 'Un riassunto di 3-5 righe',
 "Who you are, how many years in what, your strongest result. Shorter than 25 words says too little, longer than 110 isn't read.": 'Chi sei, quanti anni in quale '
                                                                                                                                   'ambito, il tuo miglior risultato. '
                                                                                                                                   'Meno di 25 parole è troppo poco; più '
                                                                                                                                   'di 110 non si legge.',
 'At least 6 skills listed': 'Almeno 6 competenze elencate',
 "Skills are what the match score and recruiters' searches look for.": 'Le competenze sono ciò che cercano il punteggio di corrispondenza e i selezionatori.',
 'Dates on every job': 'Date per ogni impiego',
 'Month or year for each job; a job without dates raises questions.': 'Mese o anno per ogni impiego; un impiego senza date solleva domande.',
 'Your last jobs say what you did': 'I tuoi ultimi impieghi dicono cosa hai fatto',
 'At least two points for each of your three most recent jobs.': 'Almeno due punti per ciascuno dei tuoi tre ultimi impieghi.',
 'Results with numbers': 'Risultati con numeri',
 'At least three points with a figure: how many people, clients, francs, percent, days. Numbers are what a reader remembers.': 'Almeno tre punti con una cifra: quante '
                                                                                                                               'persone, clienti, franchi, percentuali, '
                                                                                                                               'giorni. Sono i numeri che restano in '
                                                                                                                               'mente.',
 'Education and training listed': 'Formazione indicata',
 'Diplomas, CFC, certificates, with the year. Foreign diplomas: add the Swiss equivalent if you have it.': "Diplomi, AFC, certificati, con l'anno. Diplomi esteri: "
                                                                                                           "aggiungi l'equivalenza svizzera se ce l'hai.",
 'Languages with their level': 'Le lingue con il loro livello',
 'For example French (native), English (C1), German (A2). Almost every Swiss ad asks.': 'Per esempio italiano (madrelingua), inglese (C1), tedesco (A2). Quasi tutti gli '
                                                                                        'annunci svizzeri lo chiedono.',
 'CV ready in French': 'CV pronto in francese',
 'CV ready in German': 'CV pronto in tedesco',
 'CV ready in Italian': 'CV pronto in italiano',
 'CV ready in English': 'CV pronto in inglese',
 'You search postings in this language: with a translated profile, the CV and letter for those jobs are written in it.': 'Cerchi annunci in questa lingua: con un '
                                                                                                                         'profilo tradotto, il CV e la lettera per '
                                                                                                                         'queste offerte sono scritti in questa lingua.',
 'in French': 'in francese',
 'in German': 'in tedesco',
 'in Italian': 'in italiano',
 'in English': 'in inglese',
 'Job title': 'Titolo professionale',
 'Summary': 'Riassunto',
 'Skill': 'Competenza',
 'Job': 'Impiego',
 'Dates': 'Date',
 'Point': 'Punto',
 'Education': 'Formazione',
 'Heading of the last section': "Titolo dell'ultima sezione",
 'Line': 'Riga',
 '{n} new jobs this week': '{n} nuove offerte questa settimana',
 'Applications this month: {done} of {target}': 'Candidature questo mese: {done} su {target}',
 'Assigned by the ORP, to apply: {n}': "Assegnazioni dell'URC, da candidarsi: {n}",
 'Interviews in the next 7 days: {n}': 'Colloqui nei prossimi 7 giorni: {n}',
 'Without an answer, to follow up: {n}': 'Senza risposta, da sollecitare: {n}',
 'Interview: {title} — {company}': 'Colloquio: {title} — {company}',
 'ORP deadline: apply to {title} — {company}': 'Termine URC: candidarsi a {title} — {company}',
 'Follow up: {title} — {company}': 'Sollecitare: {title} — {company}',
 'Hand in the proofs of job search for {month}': 'Consegnare le prove delle ricerche di lavoro di {month}',
 'Job search, week {week}: {n} new jobs': 'Ricerca di lavoro, settimana {week}: {n} nuove offerte',
 'Job search': 'Ricerca di lavoro',
 'new': 'nuove',
 'shortlisted': 'da tenere',
 'applied': 'candidato',
 'interview': 'colloquio',
 'offer': 'offerta ricevuta',
 'rejected': 'rifiuto',
 'discarded': 'scartate',
 'Applied': 'Candidato',
 'Interview': 'Colloquio',
 'Offer': 'Offerta',
 'Not my kind of job': 'Non è il mio tipo di posto',
 'Too senior / too much experience asked': 'Troppo senior / troppa esperienza richiesta',
 'Too junior / internship / apprenticeship': 'Troppo junior / stage / apprendistato',
 'Too far / wrong place': 'Troppo lontano / posto sbagliato',
 "A language I don't speak": 'Una lingua che non parlo',
 'Wrong work rate or contract (part-time, temporary...)': 'Grado o contratto inadatto (tempo parziale, temporaneo...)',
 'Salary or conditions': 'Salario o condizioni',
 'Not this company / recruitment agency': 'Non questa azienda / agenzia di collocamento',
 'Duplicate / already seen': 'Doppione / già vista',
 'Position filled or expired': 'Posto occupato o annuncio scaduto',
 'Other': 'Altro',
 'Removed by a change of the search settings': 'Tolta da una modifica delle impostazioni',
 'No reason given': 'Senza motivo',
 'Skip titles with a word these jobs share (one click below), or tighten "Keep titles containing".': 'Ignora i titoli con una parola che queste offerte hanno in comune '
                                                                                                     '(un clic qui sotto), o restringi «Il titolo del posto deve '
                                                                                                     'contenere».',
 'Add words like senior, lead, head, responsable to "Skip titles containing".': 'Aggiungi parole come senior, lead, head, responsabile a «Ignora i titoli che '
                                                                                'contengono».',
 'Add words like junior, stage, stagiaire, apprenti* to "Skip titles containing".': 'Aggiungi parole come junior, stage, stagista, apprendista a «Ignora i titoli che '
                                                                                    'contengono».',
 'Stop searching the towns below with one click, or set a maximum travel time in Settings.': 'Ferma la ricerca nelle località qui sotto con un clic, o fissa un tragitto '
                                                                                             'massimo nelle Impostazioni.',
 'Remove that language from the posting languages.': 'Togli questa lingua dalle lingue degli annunci.',
 'Add words like temporaire, 20%, stage to "Skip titles containing".': 'Aggiungi parole come temporaneo, 20%, stage a «Ignora i titoli che contengono», o fissa il grado '
                                                                       'desiderato nelle Impostazioni.',
 'Never show a company or an agency again with one click below.': "Non mostrare più un'azienda o un'agenzia con un clic qui sotto.",
 'The same job came from two sites with different wording: tell the administrator which ones.': 'La stessa offerta è arrivata da due siti con una formulazione diversa: '
                                                                                                "indica quali all'amministratore.",
 'German (not in your skills)': 'Tedesco (non tra le tue competenze)',
 'French (not in your skills)': 'Francese (non tra le tue competenze)',
 'English (not in your skills)': 'Inglese (non tra le tue competenze)',
 'Italian (not in your skills)': 'Italiano (non tra le tue competenze)',
 'Work permit or nationality condition': 'Condizione di permesso di lavoro o di nazionalità',
 'Driving licence': 'Licenza di condurre',
 'A draft built from your profile for this posting and company: review and personalise it before sending.': 'Una bozza costruita a partire dal tuo profilo per questo '
                                                                                                            'annuncio e questa azienda: rileggila e personalizzala prima '
                                                                                                            "dell'invio.",
 'ok (original)': 'ok (originale)',
 'IT & technology': 'Informatica e tecnologia',
 'Sales & marketing': 'Vendita e marketing',
 'Retail': 'Commercio al dettaglio',
 'Office, customer & operations': 'Ufficio, clientela e operazioni',
 'Finance, legal & banking': 'Finanza, diritto e banca',
 'Logistics & purchasing': 'Logistica e acquisti',
 'Hospitality': 'Alberghiero e ristorazione',
 'Design': 'Design',
 'Education & training': 'Insegnamento e formazione',
 'Health care': 'Sanità',
 'Engineering & technical': 'Ingegneria e tecnica',
 'Entry level / first jobs': 'Principiante / primi impieghi',
 'Experienced (2-7 years)': 'Con esperienza (da 2 a 7 anni)',
 'Senior / expert': 'Senior / esperto',
 'Lead / manager / head of': 'Responsabile / quadro / direzione',
 'Warming up': 'In riscaldamento',
 'On the move': 'In movimento',
 'In the race': 'In gara',
 'Front runner': 'In testa al gruppo',
 'Unstoppable': 'Inarrestabile',
 'Lift-off': 'Decollo',
 'High five': 'Batti cinque',
 'Bullseye': 'Centro pieno',
 'On fire': 'In fiamme',
 'Persistent': 'Tenace',
 'Sharp eye': 'Occhio di lince',
 'Made to measure': 'Su misura',
 'On stage': 'In scena',
 'Thick skin': 'Pelle dura',
 'Polished': 'Tirato a lucido',
 'Jackpot': 'Jackpot',
 'Send your first application': 'Invia la tua prima candidatura',
 '5 applications in one week': '5 candidature in una settimana',
 'Reach the monthly target': "Raggiungi l'obiettivo mensile",
 'Apply 3 weeks in a row': 'Candidati 3 settimane di fila',
 'Follow up 3 applications': 'Sollecita 3 candidature',
 'Sort 20 jobs and say why': 'Ordina 20 offerte dicendo perché',
 'Write a CV and a letter for the same job': 'Scrivi un CV e una lettera per la stessa offerta',
 'Get an interview': 'Ottieni un colloquio',
 '5 refusals and still going': '5 rifiuti e ancora in gara',
 'Complete the profile check': 'Completa il controllo del profilo',
 'Get an offer': "Ricevi un'offerta",
 'German': 'Tedesco',
 'French': 'Francese',
 'English': 'Inglese',
 'Italian': 'Italiano',
 'native': 'madrelingua',
 'fluent': 'fluente',
 'basic': 'conoscenze',
 'Vocational diploma (CFC / EFZ / AFC)': 'AFC (attestato federale di capacità)',
 'Federal certificate or diploma (brevet, Fachausweis)': 'Attestato o diploma federale',
 'College of higher education (ES / HF)': 'Scuola specializzata superiore (SSS)',
 'Bachelor / university of applied sciences (HES / FH)': 'Bachelor / scuola universitaria professionale (SUP)',
 'Master / university (EPF, Uni)': 'Master / università (PF, Uni)',
 'Further training (CAS / DAS / MAS)': 'Formazione continua (CAS / DAS / MAS)'}
