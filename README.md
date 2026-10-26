# Mac per sviluppo: RustDesk + Chrome Remote Desktop

Sessione macOS temporanea su GitHub Actions, destinata allo sviluppo e ai test del progetto. Mantiene RustDesk come primo accesso, installa Chrome e Chrome Remote Desktop Host e crea l'amministratore aggiuntivo `remoteadmin` a ogni esecuzione.

## Prima di usare questa versione

La versione precedente caricava password in chiaro negli artifact. **Gli artifact di un repository pubblico sono scaricabili da chiunque abbia un account GitHub e accesso in lettura**: il nome dell'utente nel file non limita l'accesso. Il masking nei log non cifra gli artifact. [Documentazione GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)

Se hai gia eseguito quella versione, termina le vecchie sessioni, elimina gli artifact e i log che contengono dati sensibili e considera compromesse le credenziali pubblicate. Se qualcuno poteva collegarsi mentre usavi la VM, revoca anche sessioni/token degli account usati nel Mac e cambia le password eventualmente esposte. Una modifica al codice non elimina i dati delle esecuzioni passate o le copie gia scaricate.

Questa versione pubblica **solo un file cifrato con age**, contenente ID RustDesk e password casuali nuove per ogni sessione. La chiave privata rimane sul tuo computer. Non sono necessari password personali, chiavi private o token Google nei Secrets di GitHub.

## Configurazione iniziale (una volta)

1. Installa `age` **sul tuo computer** dalle [release ufficiali](https://github.com/FiloSottile/age/releases) e aggiungi `age` e `age-keygen` al PATH. Su Mac puoi usare `brew install age`.
2. In una cartella privata **fuori dal repository**, genera la chiave:

   ```text
   age-keygen -o remote-mac-key.txt
   age-keygen -y remote-mac-key.txt
   ```

   Il secondo comando mostra la chiave pubblica che inizia con `age1`. Conserva `remote-mac-key.txt` solo sul tuo PC, con un backup protetto: contiene la **chiave privata**. Non incollarla in chat, Secrets, log, commit o artifact. Se la perdi, non puoi recuperare le credenziali cifrate.

3. Nel tuo fork apri **Settings → Secrets and variables → Actions → Variables → New repository variable**. Nome: `AGE_RECIPIENT`. Valore: soltanto la chiave **pubblica** `age1...`.
4. Integra questa modifica nel branch predefinito. Apri **Actions → Mac development session (RustDesk + Chrome) → Run workflow**, selezionando quel branch.

Il workflow accetta solo avvio manuale e riesecuzione da parte del proprietario del repository personale. I collaboratori devono usare un proprio fork e una propria chiave. Non e una piattaforma multiutente: tutti gli artifact di questo fork sono cifrati per il destinatario impostato dal proprietario.

## Collegamento a ogni sessione

1. Attendi il completamento di **Publish ONLY encrypted connection details**. Puoi scaricare l'artifact anche mentre il job continua; non serve aspettarne la fine.
2. Scarica `encrypted-connection-<run-id>-<attempt>` dalla pagina dell'esecuzione ed estrai lo ZIP.
3. Decifra **sul tuo PC**, usando i percorsi dei tuoi file:

   ```text
   age --decrypt --identity remote-mac-key.txt --output connection-info.txt connection-info.txt.age
   ```

4. Apri `connection-info.txt`: contiene ID/password RustDesk e nome/password di `remoteadmin`. Collegati con RustDesk. Il file decifrato e sensibile: conservalo privatamente ed eliminalo quando non serve.
5. Il passaggio successivo installa e apre Chrome su `https://remotedesktop.google.com/access`. Controlla l'esito del relativo step. Se il download Google fallisce, RustDesk rimane disponibile durante la sessione per consentire il recupero manuale.

Non vengono pubblicati ID RustDesk, password, indirizzi IP, geolocalizzazione, file di configurazione o profili browser in chiaro. Sono pubblici codice, metadati e normali log di stato/installazione del workflow. Non scrivere dati personali nei comandi del workflow.

## Cosa e automatico e cosa richiede la GUI

| Operazione | Comportamento |
|---|---|
| RustDesk | Download della release fissata, verifica SHA-256 e firma, avvio diretto dalla sessione grafica del runner e password casuale verificata tramite CLI |
| Chrome | Installazione dal DMG ufficiale, verifica firma Google e Gatekeeper, apertura della pagina CRD |
| Chrome Remote Desktop Host | Installazione del pacchetto firmato Google, registrazione del LaunchAgent nella sessione GUI corrente e apertura della procedura ufficiale dei consensi |
| Amministratore aggiuntivo | Creazione di `remoteadmin`, home privata, verifica gruppo admin e autenticazione con password |
| Account Google e PIN CRD | Da configurare nella GUI attraverso RustDesk |
| Accessibilita e registrazione schermo | Consensi macOS da concedere quando richiesti; possono essere limitati dalla VM |
| Sessione grafica di `remoteadmin` | Non viene effettuato automaticamente il cambio utente; l'account serve anzitutto per autenticare le operazioni amministrative |

In Chrome, accedi a Google, abilita l'accesso remoto, scegli nome e PIN e concedi i permessi richiesti in **Impostazioni di Sistema → Privacy e sicurezza**. Quando compare un dialogo amministrativo, usa `remoteadmin` e la password decifrata. Verifica una connessione CRD da un secondo dispositivo prima di affidarti a quel canale. [Guida ufficiale Google](https://support.google.com/chrome/answer/1649523?hl=it)

### Attivazione dopo il PIN e consensi mancanti

La richiesta macOS di nome utente e password subito dopo il PIN autorizza l'attivazione del servizio. Non e un login al desktop: `remoteadmin` serve per quell'autorizzazione e la sessione grafica rimane quella del runner. Il codice verifica password e gruppo admin, ma questo non dimostra che il servizio Google si sia poi avviato. Non e stato dimostrato che il problema richieda Secure Token o una password diversa.

Il pacchetto installato da `sudo installer` puo non caricare il LaunchAgent nel desktop gia aperto: il postflight upstream, su un'installazione nuova, usa la variabile `USER` quando e diversa da root. Il workflow ora registra esplicitamente il job Google in `gui/<uid>` e apre, come utente console, il native host Google con il parametro upstream `--check-permission`. Non abilita automaticamente i consensi e non modifica TCC.db. L'installer non disabilita i consensi; da solo non garantisce che la procedura venga mostrata nel desktop dell'utente.

Compare sul desktop il collegamento **Chrome Remote Desktop - Permessi.command**: puoi aprirlo per richiamare la preparazione e la procedura ufficiale. Autorizza il componente dell'**accesso permanente** quando richiesto: i controlli Google distinguono questo componente da quello dell'assistenza remota. L'assistenza funzionante non prova che l'accesso permanente sia configurato o abbia gli stessi consensi.

Per una sessione gia avviata con la versione precedente, puoi provare questa riparazione nel **Terminale del Mac remoto**, mantenendo RustDesk aperto. Non richiede un nuovo job e non usa `sudo` per i consensi:

```bash
launchctl enable "gui/$(id -u)/org.chromium.chromoting"
launchctl print "gui/$(id -u)/org.chromium.chromoting" >/dev/null 2>&1 || launchctl bootstrap "gui/$(id -u)" /Library/LaunchAgents/org.chromium.chromoting.plist
CRD_NATIVE_HOST="$(plutil -extract path raw -o - /Library/Google/Chrome/NativeMessagingHosts/com.google.chrome.remote_desktop.json)"
"$CRD_NATIVE_HOST" --check-permission
```

Completa la procedura, poi torna a `remotedesktop.google.com/access` e ripeti l'attivazione. Se il componente permanente non compare, cerca nel Finder **Vai → Vai alla cartella** il percorso `/Library/PrivilegedHelperTools/`: nelle versioni correnti il bundle e `ChromeRemoteDesktopHost.app`. Puoi selezionare il componente tramite il pulsante `+` nelle impostazioni di privacy dove disponibile, senza rimuovere i permessi dell'assistenza gia funzionante. I nomi mostrati possono variare con la versione del pacchetto.

Fonti del comportamento: [postflight ufficiale Chromium](https://chromium.googlesource.com/chromium/src/+/main/remoting/host/installer/mac/Scripts/remoting_postflight.sh), [controllo del servizio e autorizzazione amministrativa](https://chromium.googlesource.com/chromium/src/+/main/remoting/host/setup/daemon_controller_delegate_mac.mm), [procedura dei consensi](https://chromium.googlesource.com/chromium/src/+/main/remoting/host/setup/me2me_native_messaging_host_main.cc), [componenti distinti per i consensi](https://chromium.googlesource.com/chromium/src/+/main/remoting/host/mac/permission_checker.cc).

Installare l'Host non equivale a registrarlo sul tuo account Google. Il workflow non tenta di riutilizzare token OAuth o copiare un profilo Chrome. La VM viene ricreata a ogni job: installazione e account macOS sono automatici, ma login Google, registrazione e consensi possono dover essere ripetuti. Non viene promesso un avvio CRD gia autenticato.

L'appartenenza al gruppo `admin` non concede automaticamente Secure Token, sblocco FileVault, autorizzazioni TCC o privilegi superiori alle limitazioni del runner. Non sono aggiunti sudo senza password al nuovo account, modifiche dirette al database TCC o disabilitazioni di SIP/Gatekeeper.

**Primo accesso RustDesk:** il servizio viene avviato e configurato, ma uno schermo e un ID non dimostrano che cattura schermo e controllo tastiera funzionino. Se l'immagine del runner richiede un consenso interattivo prima del primo accesso, il workflow non puo garantirne il superamento. In quel caso serve un Mac/runner controllato da te, con i consensi gia concessi; creare un altro admin non risolve quel vincolo.

**Connesso, in attesa dell'immagine:** la connessione e stata stabilita, ma il video non arriva. Il processo di cattura viene avviato direttamente come figlio del workflow nella sessione console, senza LaunchAgent/LaunchDaemon: e una correzione della regressione introdotta dal precedente avvio tramite launchd. Su alcuni sistemi macOS 26 e stato segnalato un problema di cattura con quell'avvio; la segnalazione non dimostra da sola la causa su tutte le VM. [Discussione upstream](https://github.com/rustdesk/rustdesk/discussions/15364)

Il workflow controlla che utente console e runner coincidano, che WindowServer e il processo RustDesk siano attivi, risveglia il display e segnala errori di cattura riconosciuti con messaggi fissi. Non acquisisce screenshot e non pubblica log grezzi. Questi controlli non sono una prova di consegna del primo fotogramma: serve una connessione dal client. Se il problema persiste, prova dal client un codec software come VP9 o disattiva il codec hardware, e verifica i consensi macOS attraverso un canale gia disponibile. [Guida ufficiale RustDesk](https://rustdesk.com/blog/rustdesk-connected-waiting-for-image/)

La sessione grafica del runner deve rimanere aperta. Il cambio utente/logout e l'accesso alla schermata di login non sono supportati da questa modalita; `remoteadmin` rimane disponibile per autenticare i dialoghi nella sessione corrente.

### Evitare di riscrivere l'utente nei dialoghi amministrativi

Nel modulo **Run workflow** puoi selezionare **configure_console_password**. E disattivato per impostazione predefinita. Se attivato su un runner GitHub-hosted, imposta una password casuale per l'account gia aperto nel desktop, verifica che sia gia amministratore e prova l'autenticazione. Le voci **macOS console user** e **macOS console password** vengono aggiunte soltanto al file cifrato. Quando un dialogo propone quell'account puoi lasciare il nome e inserire la sua password. `remoteadmin` rimane disponibile come account aggiuntivo, con password separata.

L'opzione non effettua logout, cambio utente o login automatico, non modifica le regole di autorizzazione e non elimina le richieste di password o i consensi di privacy. Il nome proposto dipende dal singolo dialogo, quindi non e garantito che ogni app preselezioni lo stesso account. Se l'account console non e gia amministratore, la preparazione fallisce: non lo promuove automaticamente. Il reset viene rifiutato sui runner self-hosted e fuori da GitHub Actions.

**Effetto sul portachiavi:** il reset dell'account non cambia la password di un portachiavi login gia presente. Questo puo impedirne lo sblocco automatico o generare richieste della vecchia password. Il workflow non cancella ne resetta il portachiavi, non tenta di ricavarne la password e non modifica Secure Token/FileVault. Se dipendi da certificati o credenziali preesistenti nel portachiavi, lascia l'opzione disattivata e usa `remoteadmin`. [Guida Apple sul portachiavi](https://support.apple.com/en-gb/guide/keychain-access/kyca2429/mac)

### Si possono preattivare tutti gli switch di privacy?

Non con un comando supportato che conceda entrambi i permessi su questo runner. Registrazione schermo richiede il consenso dell'utente; anche i profili PPPC non la possono concedere silenziosamente. Accessibilita puo essere gestita tramite PPPC/MDM su Mac gestiti, ma questo progetto non iscrive il runner a un MDM. `tccutil` non e un comando per concedere questi permessi. Apriamo la procedura ufficiale; non modifichiamo TCC.db e non disabilitiamo SIP. [Policy PPPC Apple](https://support.apple.com/en-gb/guide/deployment/dep38df53c2a/web)

Su un Mac sotto il tuo controllo e possibile configurare un account per il login automatico, ma quel login avviene all'avvio. Qui il workflow parte dopo l'apertura della sessione del runner e crea l'account aggiuntivo in quel momento. Un cambio di sessione potrebbe perdere il contesto grafico/TCC di RustDesk e richiedere nuovamente i consensi; non e una sostituzione affidabile per l'opzione delle credenziali console. [Login automatico secondo Apple](https://support.apple.com/en-gb/102316)

## Protezioni e limiti di riservatezza

- Credenziali generate con un generatore crittografico; ID e password consegnati soltanto tramite cifratura a chiave pubblica. La chiave privata non raggiunge il runner.
- File temporanei in `RUNNER_TEMP`, permessi `700` sulle directory e `600` sui file. Nessuna password in `GITHUB_ENV`, `GITHUB_OUTPUT`, summary, cache o artifact in chiaro. Il JSON temporaneo viene rimosso dopo la cifratura.
- RustDesk richiede la password permanente; accesso tramite solo clic, password temporanea, discovery LAN, server diretto, tunnel e terminale sono disattivati. Le impostazioni RustDesk vengono verificate tramite CLI prima di pubblicare l'artifact. Nessun dump dei file TOML o dei processi nei log.
- Token Actions con solo `contents: read`, checkout senza credenziali persistenti, action fissate a SHA e nessuna esecuzione su pull request. Nessuna rotazione IP, telemetria IP o cache della cronologia.
- Nessuna porta VNC/SSH aggiuntiva viene abilitata. I vecchi workflow VNC e auto-chain sono rimossi per eliminare altri percorsi che pubblicavano credenziali.
- Cleanup finale al meglio delle possibilita, anche dopo errori. In caso di terminazione forzata puo non essere eseguito: la distruzione del runner ospitato resta il confine finale della sessione. Non usare questo script su un Mac personale o un runner persistente senza adattarne il ciclo di vita.

**Non esiste una garanzia di riservatezza assoluta.** GitHub e il provider della VM, processi con privilegi root, software installato o chi puo modificare il workflow possono accedere ai dati durante la sessione. Le CLI di sistema e RustDesk richiedono brevemente password negli argomenti dei processi locali: l'output viene catturato e mai stampato. Il masking e una difesa aggiuntiva, non il confine di sicurezza.

Chi legge soltanto la repo riceve il codice e l'artifact cifrato, senza ottenere per questo il desktop. Chi puo scrivere codice fidato puo invece cambiare il destinatario o esfiltrare dati: limita i collaboratori, proteggi il branch predefinito e verifica modifiche a script/workflow e `AGE_RECIPIENT`. Non eseguire codice di PR sconosciute nella sessione in cui accedi ai tuoi account. Per dati personali sensibili scegli un Mac dedicato sotto il tuo controllo. Usa account di sviluppo e MFA; evita la sincronizzazione del profilo browser personale.

La cifratura protegge la consegna delle credenziali, non nasconde i dati all'host o ai software della sessione. Le cancellazioni non garantiscono una sovrascrittura fisica sicura del disco virtuale.

## Durata, costi e uso consentito

I runner standard GitHub-hosted nei repository pubblici non consumano minuti fatturabili, ma **non sono senza limiti**. Un job ospitato dura al massimo 6 ore; questa configurazione limita la sessione a 1–5 ore, lasciando margine per installazione e cleanup. Non concatena automaticamente nuovi job. Non viene promesso un IP dedicato o una sessione persistente. [Billing](https://docs.github.com/en/actions/concepts/billing-and-usage), [limiti](https://docs.github.com/en/actions/reference/limits)

L'uso dei runner ospitati deve essere legato alla produzione, ai test, al deployment o alla pubblicazione del progetto associato al repository. Non e un servizio gratuito per un desktop personale permanente. Usalo per sviluppo/test Xcode del progetto e una sola persona per VM. [Termini specifici GitHub Actions](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions)

Sono selezionabili solo runner standard `macos-15` e `macos-26`. Eventuali runner piu grandi richiedono verifica separata di disponibilita e fatturazione.

## Prestazioni e alternative

Non c'e un benchmark eseguito su questa VM che dimostri un vincitore. La latenza dipende da distanza dal datacenter, collegamento diretto o relay, codec, risoluzione e accelerazione video disponibile nel guest. Una VPN non riduce automaticamente la latenza e puo aumentarla.

| Soluzione | Valutazione per questo progetto |
|---|---|
| Chrome Remote Desktop | Comodo per account Google e collegamento dal browser. Installato; registrazione manuale |
| RustDesk | Primo accesso e recupero; prova qualita orientata alla velocita, risoluzione inferiore e controlla se la connessione passa da relay |
| Parsec | Candidato da confrontare per fluidita. Installazione opzionale `install_parsec`, disattivata per velocizzare l'avvio; login e consensi manuali. Hosting Mac supportato, prestazioni del guest da verificare |
| NoMachine | Candidato valido: H.264 e accelerazione hardware Mac supportati. Non e dimostrato piu veloce su questa VM. La versione gratuita via IP richiede raggiungibilita; qui avrebbe senso una rete privata con ACL oppure NoMachine Network (abbonamento). Non viene installato o esposto automaticamente |
| Sunshine + Moonlight | Progettato per streaming a bassa latenza; supporto macOS sperimentale e accelerazione del guest da verificare. Non incluso come servizio aggiuntivo |

Per confrontare, usa lo stesso client e la stessa VM, rete e risoluzione (ad esempio 1920×1080), quindi osserva digitazione, scorrimento in Xcode, frame persi e statistiche di rete/codec. Non confondere il ping con l'intera latenza di acquisizione, codifica, trasporto e visualizzazione.

Fonti: [Parsec su macOS](https://support.parsec.app/hc/en-us/articles/32381555792148-Install-Parsec-App-on-macOS), [NoMachine e codec](https://kb.nomachine.com/AR10K00706), [NoMachine via IP o Network](https://kb.nomachine.com/AR10Q01053), [Sunshine macOS](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html), [impostazioni RustDesk](https://rustdesk.com/docs/en/self-host/client-configuration/advanced-settings/).

## Verifica e manutenzione

I controlli locali coprono sintassi Bash/Python/YAML, vincoli del workflow, fallimenti delle CLI, diagnostica senza esposizione dei log e cifratura/decifratura age. Non sostituiscono un test su una vera VM macOS: firma dei pacchetti, avvio nella sessione grafica, account e consensi TCC devono essere verificati al primo avvio autorizzato. Il workflow non viene lanciato automaticamente da questa modifica.

Per aggiornare RustDesk, aggiorna insieme release e digest in `scripts/setup-rustdesk.sh` e verifica che le CLI continuino a raggiungere il processo `--server` dell'utente console. Chrome, CRD e Parsec provengono dagli URL ufficiali correnti e passano la verifica della firma/Gatekeeper; non sono byte-per-byte riproducibili. age proviene dalla formula Homebrew.
