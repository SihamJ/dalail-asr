# dalail-asr — محاذاة الدلائل والهمزية

Transcription ASR au niveau du mot et alignement de texte pour deux
enregistrements de munshid, avec un outil de vérification à l'oreille :

- **الهمزية** (`hamzia.mp3`, ~2 h) — la qasida d'البوصيري, alignée sur
  ses 462 vers.
- **دلائل الخيرات** (`dalail-marrakchiya.mp3`, ~2 h ¼, المراكشية) —
  alignée sur les segments ordonnés extraits du JSON de l'application
  Dalail elle-même.

## L'outil de vérification

```bash
./review.sh          # sert ce dossier sur :8097 et ouvre la page
```

Ou ouvrez simplement `review.html` directement — l'audio est diffusé
depuis R2 (`pub-…r2.dev`), la page fonctionne donc sans aucun mp3 local.
(NB : `pub-….r2.dev` est le point de
terminaison de *développement* de R2, limité en débit et ralenti sous
charge réelle. Un domaine personnalisé règle cela en cinq minutes.)

Dans la page : les deux boutons changent d'enregistrement ; cliquez sur
une ligne pour y amener l'audio ; la ligne en cours de lecture se
surligne et suit. **Les lignes orange sont des positions estimées
seulement** (interpolées entre les ancres) — ce sont elles qui demandent
une oreille. L'en-tête compte تلقائي et للمراجعة.

### Corriger les positions

Cliquez sur une ligne et le **banc d'édition** monte du bas de la page,
avec une molette pour البداية et une pour النهاية :

- **⏹ هنا** — estampille la tête de lecture : laissez l'audio courir
  jusqu'au vrai bord, appuyez, c'est fait. (Même geste que l'outil des
  frontières intro/outro.)
- **±0.3** — décale de 0,3 s ; le bord se rejoue aussitôt, l'oreille
  juge la nouvelle position sans clics supplémentaires.
- **▶** — rejoue un bord. Le début se joue depuis lui-même ; la fin se
  joue depuis deux secondes *avant* elle, car entendre une fin demande
  un élan.
- **استرجاع** — abandonne les corrections de la ligne et revient aux
  temps de l'aligneur.

Les lignes corrigées prennent un **bord vert** et perdent leur drapeau
orange — vert signifie qu'un humain a répondu, quoi qu'en pense
l'aligneur. Une fin ne peut jamais précéder son début (l'autre bord est
entraîné si on le dépasse), mais les lignes voisines ne sont
délibérément PAS répercutées — les chevauchements entre lignes sont
permis et enregistrés tels quels.

Les corrections **s'enregistrent automatiquement dans le navigateur**
(localStorage) : fermer l'onglet ne perd rien — mais elles vivent dans
ce seul navigateur tant qu'elles ne sont pas exportées :
**« تنزيل التعديلات (n) »** dans l'en-tête télécharge
`dalail_time_overrides.json`, indexé par enregistrement puis par index
de ligne dans `review_data.js`, chaque entrée portant `t0`/`t1` en
secondes et un extrait du libellé pour que le fichier se lise seul.
Committez ce fichier ici à la fin d'une séance de vérification ; c'est
la copie durable.

## Le pipeline (comment les données ont été produites)

1. **Transcription** — `hamzia_transcribe.py` / `dalail_transcribe.py`,
   exécutés sur le GPU, faster-whisper large-v3 avec
   `vad_filter=False` : le VAD entend la mélodie, décide « musique, pas
   parole », et ne garde presque rien d'une qasida chantée. Sortie :
   `*.asr.json` avec horodatage par mot.
2. **Texte de référence** — `hamzia_verses.json` (les vers de la
   qasida) ; `extract_dalail_segments.py` extrait `dalail_segments.json`
   du JSON embarqué de l'application Dalail.
3. **Alignement** — `hamzia_match.py` / `dalail_match.py` :
   Needleman-Wunsch en bande sur les deux flux de mots, avec scores
   flous (les déformations de Whisper restent proches du rasm :
   الأمياء≈الأنبياء) et des trous bon marché (interludes et coupures
   font ~40 % de l'audio). Les lignes sans ancre reçoivent des
   intervalles interpolés et un drapeau REVIEW. Sortie :
   `*_labels.txt` (étiquettes Audacity) — et les mêmes lignes
   sérialisées dans `review_data.js` pour la page.

Le docstring de `hamzia_match.py` consigne pourquoi la v1 (difflib
global) et la v2 (fenêtre glissante) ont échoué ; gardez l'alignement
global en bande de la v3 si un nouvel enregistrement arrive.

## Fichiers

| fichier | rôle |
|---|---|
| `review.html` + `review_data.js` | la page de vérification et ses données |
| `review.sh` | servir + ouvrir |
| `*.asr.json` | sortie ASR au niveau du mot |
| `*_match.py` | l'aligneur (écrit les étiquettes ; ses lignes nourrissent `review_data.js`) |
| `*_labels.txt` | pistes d'étiquettes Audacity |
| `hamzia_verses.json`, `dalail_segments.json` | textes de référence |
| `*.mp3` | les enregistrements (gitignorés ; aussi sur R2) |
