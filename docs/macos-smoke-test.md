# Primo avvio macOS

Questo test richiede un job ospitato macOS reale. I test locali con CLI simulate non dimostrano il funzionamento di launchd, TCC o della sessione grafica. Non usare account personali sensibili durante la verifica.

1. Configura `AGE_RECIPIENT` con una chiave pubblica di cui possiedi la chiave privata sul tuo PC. Integra il workflow nel branch predefinito e avvialo manualmente dal tuo account proprietario, scegliendo una sessione di un'ora.
2. Verifica che il preflight fallisca prima della creazione di account/servizi se la variabile e assente o non valida. Non inserire password negli input del workflow.
3. Con una variabile valida, verifica creazione di `remoteadmin`, autenticazione e appartenenza ad `admin`. Un Secure Token non viene promesso.
4. Scarica l'artifact mentre il job e in corso. Deve contenere unicamente `connection-info.txt.age`. Decifralo localmente. Controlla che log e summary non mostrino ID, password o dump di configurazione.
5. Collegati con ID e password RustDesk. Verifica immagine, mouse e tastiera. Un ID valido non prova che i permessi TCC siano concessi. Se il primo accesso e bloccato dai consensi macOS, termina il test: non disabilitare SIP e non modificare TCC.db. Servira un runner/Mac preparato con i consensi necessari.
6. Controlla l'esito di installazione Chrome/CRD. In `/Applications` deve esserci Chrome e il pacchetto Host deve risultare installato. La pagina di configurazione si apre nel desktop gia attivo; non viene effettuato un cambio utente automatico.
7. Attraverso RustDesk completa la registrazione Google usando un account di test, il PIN e i consensi richiesti. Prova CRD da un secondo dispositivo. Usa `remoteadmin` nei dialoghi amministrativi, senza confondere admin con superamento delle restrizioni della VM.
8. Selezionando `install_parsec`, prova anche Parsec con identiche rete, risoluzione e azioni in Xcode. Registra le statistiche disponibili e il percorso diretto/relay. Non attribuire al software la latenza geografica.
9. Annulla il job. Verifica l'esecuzione del cleanup quando consentita da Actions e la disconnessione dei client al termine del runner. Rimuovi il dispositivo CRD di test dal tuo account Google e revoca eventuali sessioni di test.
10. Una seconda esecuzione deve avere nuove credenziali e nuovo account. Nessun profilo browser, token Google o dato personale deve essere ripristinato da cache/artifact. Elimina il file di connessione decifrato dal tuo PC quando non serve.

Se Google cambia firma, formato DMG o identificativo del pacchetto, il relativo step deve segnalare il fallimento, mantenendo il canale RustDesk per il recupero. Non rimuovere i controlli di firma per far proseguire l'installazione.
