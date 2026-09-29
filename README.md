# dalail-asr — محاذاة الدلائل والهمزية والبردة

Alignement texte–audio, **au niveau de la ligne et du mot**, pour deux
enregistrements de munshid, avec des outils de vérification à l'oreille :

- **الهمزية** (`hamzia.mp3`, ~2 h) — la qasida d'البوصيري, 462 vers.
- **دلائل الخيرات** (`dalail-marrakchiya.mp3`, ~2 h ¼, المراكشية) — les
  segments ordonnés extraits du JSON de l'application Dalail elle-même.

**Nouveau (septembre 2026)** — le timing est désormais calculé par
**alignement forcé CTC** avec un modèle acoustique entraîné sur la
récitation coranique (dossier `new/`). Il remplace l'ancien pipeline
Whisper + appariement (dossier `old/`), conservé tel quel pour
référence. Les livrables à la racine viennent du nouveau pipeline.

## Se repérer dans le dépôt

```
dalail_labels.txt        ┐
hamzia_labels.txt        │ LIVRABLES (nouveau pipeline) — même format
review_data.js           ┘ qu'avant : une étiquette par ligne
dalail_word_labels.txt   ┐ nouveau : une étiquette par MOT
hamzia_word_labels.txt   ┘
dalail_words.json        ┐ nouveau : tout, en secondes, pour une
hamzia_words.json        ┘ application (lignes, passages, mots)

dalail_segments.json     textes de référence (entrée des deux pipelines)
hamzia_verses.json
extract_dalail_segments.py   extrait dalail_segments.json de l'app Dalail

word_review.html (+ word_review_data.js, word_review.sh)
                         vérifier le timing MOT PAR MOT, ancien vs nouveau
review.html (+ review.sh)    vérifier et corriger les LIGNES

new/                     LE PIPELINE ACTUEL (alignement forcé CTC)
  run.sh                 tout, pour un enregistrement (n'importe lequel)
  emit.py → find_lines.py → decide.py → fill_gaps.py → export.py
  ctc.py                 le cœur commun aux deux passes de recherche
  text_from_txt.py       préparer le texte d'un nouvel enregistrement
  word_review_data.py    les données de word_review.html
  requirements.txt
old/                     L'ANCIEN PIPELINE (Whisper + appariement)
  *_transcribe.py, *.asr.json, *_match.py, *_labels.txt, review_data.js
```

## Les textes officiels de l'application (`app/`)

Les trois fichiers de `app/` sont les textes **tels que l'application
Dalail les exporte** pour chaque enregistrement (sections → segments) :

| fichier | enregistrement | sorties |
|---|---|---|
| `app/dalail-nourach.json` | `dalail-nourach.mp3` (~2 h 28) | `nourach_*` |
| `app/dalail-marrakchiya.json` | `dalail-marrakchiya.mp3` (~2 h 16) | `marrakchiya_*` |
| `app/burda-app.json` | `burda.mp3` (~1 h 53) | `burda_*` |

Ils ne sont **jamais modifiés** : `new/app_json_to_text.py` les lit et
écrit à côté le texte du pipeline (`*_text.json`). Chaque ligne y garde
l'identifiant de son segment, donc chaque sortie (`*_words.json`) se
rattache directement aux segments de l'application — jusqu'aux 201 noms
du Prophète ﷺ, une ligne par nom (`prophet_name_001`…), pour remplir
leurs `audioStartMs` / `audioEndMs`. En mode `expanded` (Nourach) chaque
nom est chanté avec sa salutation, qui fait partie de la ligne ; en mode
`grouped`, le nom seul.

Des lignes sont marquées `"chanted": false` (jamais cherchées — ce n'est
qu'un champ ajouté, le texte est intact) :

- les `checkpoint` (« نجز الربع الأول… ») et trois notes de l'édition
  (« ثم تدعو بهذا الدعاء… », « قال رسول الله… من قرأ هذه الصلاة… »,
  « وفي رواية: »), dans les deux Dalail ;
- **Marrakchiya** : toute la section d'introduction (titre, أسماء النبي ﷺ,
  الاستعاذة, les 201 noms, le poème qui les suit) — cet enregistrement
  commence directement à la Fatiha du premier hizb (0:00), puis « إن الله
  وملائكته » (0:20), « وصلى الله على سيدنا… » (0:35), et ne contient les
  noms nulle part.

```bash
python new/app_json_to_text.py app/dalail-nourach.json nourach_text.json \
    --not-chanted dalail_hizb_01_monday_s033,dalail_hizb_05_friday_s024,dalail_hizb_05_friday_s025
new/run.sh nourach dalail-nourach.mp3 nourach_text.json
# Burda : le fichier contient déjà des temps par vers → étiquettes a priori
python new/app_json_to_text.py app/burda-app.json burda_text.json --prior new/work/burda_prior.txt
new/run.sh burda burda.mp3 burda_text.json new/work/burda_prior.txt
```

| | Nourach | Marrakchiya | Burda |
|---|---|---|---|
| lignes du texte | 483 | 484 | 174 |
| … marquées non chantées | 8 | 214 | 0 |
| lignes placées | 458 | 267 / 270 chantables | 174 / 174 |
| noms du Prophète ﷺ placés | 193 / 201 | (non récités) | — |
| lignes répétées | 1 | 2 | 4 |

Restent à écouter (`review.html#nourach/missing`, `#marrakchiya/missing`) :

- **Nourach** : les 8 vers du poème attribué à l'auteur, à la fin (sans
  doute non récités), 8 noms isolés et une صلاة du mardi (s011).
- **Marrakchiya** : les trois صلوات du samedi s001–s003, que ce munshid
  ne récite pas (vérifié à l'oreille sur le texte précédent).

Les 201 noms sont alignés **d'un bloc**, dans l'ordre (étape 3 bis) :
chaque ligne y est « (سيدنا) + le nom + la même salutation », et cherchée
seule, la salutation commune trouvait 201 places presque égales — un nom
glissait sur l'audio de son voisin. En bloc, chaque salutation prend son
tour, et seuls les noms décident.

Les fichiers `dalail_*` ci-dessous restent l'alignement du même
enregistrement sur le texte du livre (`dalail_segments.json`), antérieur
à ces exports.

## Les livrables

**`*_labels.txt`** — une étiquette Audacity par ligne, exactement au
format d'avant : `début⇥fin⇥[REVIEW ]vNNN <40 premiers caractères>`, en
secondes. Une ligne chantée deux fois porte **deux étiquettes** (même
`vNNN`, dans l'ordre du temps). `REVIEW` marque une ligne non trouvée dans
l'audio (son intervalle est alors interpolé entre ses voisines, comme
avant) ou placée avec une confiance faible.

**`*_word_labels.txt`** — une étiquette Audacity par mot :
`début⇥fin⇥vNNN.MM mot` (mot MM de la ligne NNN) ; le 2ᵉ passage d'une
ligne répétée s'écrit `vNNNp2.MM`. Importable dans Audacity comme piste
d'étiquettes, par-dessus l'audio.

**`*_words.json`** — pour une application :

```json
{"recording": "hamzia", "units": "secondes", "lines": [
  {"v": 1, "id": "hamzia_opening_b001", "text": "…", "sung": true,
   "review": false, "optional_sung": null,
   "passes": [{"t0": 0.16, "t1": 13.84, "score": -0.07,
               "words": [{"w": "صَلِّ", "t0": 0.16, "t1": 1.10}, …]}]}]}
```

`passes` a un élément par fois où la ligne est chantée (vide si elle ne
l'est pas). `found_in_gap` vaut `true` pour une ligne retrouvée par la
seconde passe (voir l'étape 3 bis) : ce sont les premières à écouter.
`cut` vaut `true` pour une ligne coupée par le bord de l'enregistrement :
seuls ses mots présents ont un temps. `optional_sung` dit si les mots entre parenthèses — `(سَيِّدِنَا)`
— ont été retenus comme chantés (voir « Limites »). Pour surligner, prenez
`t0` de chaque mot : le mot reste allumé jusqu'au `t0` du suivant.

**Résultats**

| | Dalail | Hamziyya |
|---|---|---|
| lignes placées | 267 / 280 | 441 / 462 |
| … dont retrouvées dans leur trou (étape 3 bis) | 67 | 37 |
| lignes répétées | 2 | 15 |
| lignes REVIEW | 19 | 22 |
| mots avec un temps — ancien pipeline | 53 % | 45 % |
| mots avec un temps — nouveau | 100 % des lignes placées | 100 % des lignes placées |

Toutes les lignes non placées ont été écoutées une à une :

- **Dalail** (13) : les 10 titres et notes de l'édition, que le munshid
  ne chante pas (« أسماء سيدنا… », « ثم تدعو بهذا الدعاء… », « نجز الربع
  الأول… », etc.) — marqués `"chanted": false` dans `dalail_segments.json`,
  voir plus bas ; et **v189–v191**, que ce munshid ne récite pas : il
  enchaîne v188 (1:31:24) et v192 (1:31:39), vérifié à l'oreille.
- **Hamziyya** (21) : l'enregistrement s'arrête net à 1:57:01, en plein
  v441 (« …فقامت تغار », placé et marqué `cut`) ; v442–v462 n'y sont donc
  pas.

## Pourquoi un nouveau pipeline

L'ancien prenait les temps des mots chez Whisper. Or Whisper ne mesure pas
le son : ses frontières de mots viennent de l'endroit où « regarde » son
attention. Sur une voix qui tient une syllabe (madd, mélisme), la frontière
tombe au milieu de la voyelle tenue et le surlignage **part en avance** ;
et beaucoup de mots du livre n'étaient jamais appariés à un mot de Whisper
(ils n'avaient aucun temps). Mesuré sur des versets récités avec tajwīd :
44 % des mots démarraient plus de 300 ms trop tôt.

L'**alignement forcé CTC** part du texte connu : le modèle donne, pour
chaque tranche de 20 ms de son, la probabilité de chaque lettre, et le
chemin le plus probable attribue chaque tranche à une lettre du texte. Une
voyelle tenue reste donc dans son mot ; la frontière tombe là où sonne la
première lettre du mot suivant. Modèle :
[`rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final`](https://huggingface.co/rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final)
(wav2vec2, entraîné sur la récitation coranique ; son alphabet inclut les
voyelles, on lui donne donc le texte vocalisé). Vérification croisée
faite avec un modèle indépendant (`facebook/mms-1b-all`) : ils placent les
mêmes frontières à 100 ms près pour ~90 % des mots.

## Le nouveau pipeline, étape par étape

1. **`new/emit.py`** — les probabilités de lettres pour tout
   l'enregistrement, une fois (fenêtres de 20 s qui se chevauchent).
2. **`new/find_lines.py`** — chaque ligne est cherchée dans l'audio autour
   de sa position a priori, avec un « joker » qui absorbe tout ce qui n'est
   pas elle (autres lignes, interludes, silence). Jusqu'à 5 emplacements
   candidats par ligne. Les lignes à mots entre parenthèses sont essayées
   avec et sans eux.
3. **`new/decide.py`** — tout le texte décidé ensemble : un emplacement
   par ligne, dans l'ordre du livre, aucun tronçon d'audio attribué deux
   fois ; une ligne sans emplacement convenable est « non chantée ». Les
   autres candidats d'une ligne situés juste après elle sont ses
   **répétitions**.
3 bis. **`new/fill_gaps.py`** — la seconde passe. Ces textes se
   répètent (formules du Dalail, rimes et tournures de la Hamziyya) : le
   meilleur candidat d'une ligne était parfois la même formule ailleurs,
   hors de l'ordre du livre, donc refusé à juste titre — et la ligne
   perdue alors qu'elle est chantée. Pire : une voisine pouvait s'être
   posée sur son audio (une formule en vaut une autre), ne lui laissant
   aucun trou. Chaque trou est donc réaligné **avec ses voisines** :
   0 à 6 lignes placées de chaque côté sont reprises, et tout le bloc est
   aligné **ensemble, dans l'ordre**, avec un joker avant, entre et après
   les lignes (interludes, silence) — chacune ne peut prendre que sa place
   dans la suite. On garde la version qui score le mieux (même objectif
   qu'à l'étape 3 : chaque ligne placée vaut son score + 1,6), si elle
   bat l'existant.
   - Une ligne placée par l'étape 3 peut **bouger, jamais disparaître** ;
     seules les lignes manquantes peuvent rester de côté.
   - Tant qu'une ligne colle mal (score < −1,6 : l'ordre tient déjà la
     ligne, on accepte un chant plus rapide qu'à l'étape 3), on en retire
     une — pas forcément la pire : des lignes absentes forcées dans le
     bloc écrasent les lignes chantées, qui scorent alors aussi mal. On
     essaie les six pires et retire celle dont le départ profite le plus
     au bloc. Puis on tente d'ajouter chaque ligne laissée de côté, de
     l'échanger contre une voisine proche, et l'autre lecture des mots
     optionnels « (سيدنا) » (sans elle, v188 et v189 du Dalail scorent à
     égalité).
   - Au bord de l'enregistrement, une ligne peut être coupée en plein
     chant : si elle n'entre pas en entier dans le dernier trou, on place
     son début (le plus long qui colle et va jusqu'à la fin du fichier) —
     de même pour la fin d'une ligne au tout début.
   - Les lignes marquées `"chanted": false` dans le texte ne sont jamais
     cherchées.
4. **`new/export.py`** — les livrables ci-dessus, et `review_data.js`.

`new/run.sh` enchaîne le tout. La position a priori vient des
étiquettes de l'ancien pipeline (`old/*_labels.txt`) ; sans elles, les
lignes sont réparties proportionnellement au nombre de mots et la fenêtre
de recherche est élargie (voir plus bas).

## Relancer le pipeline

Il faut **Python 3.10+**, **ffmpeg**, et de préférence un **GPU NVIDIA**.

```bash
pip install -r new/requirements.txt       # torch, torchaudio, transformers, numpy
# les mp3 ne sont pas dans git : les récupérer depuis R2
curl -O https://pub-399f14501bad46a28b40e12c0215d805.r2.dev/hamzia.mp3
curl -O https://pub-399f14501bad46a28b40e12c0215d805.r2.dev/dalail-marrakchiya.mp3

new/run.sh hamzia hamzia.mp3 hamzia_verses.json old/hamzia_labels.txt
new/run.sh dalail dalail-marrakchiya.mp3 dalail_segments.json old/dalail_labels.txt
python new/word_review_data.py            # les données de word_review.html
```

Le modèle (~1,2 Go) se télécharge tout seul depuis Hugging Face au premier
lancement. Les fichiers intermédiaires vont dans `new/work/` (ignoré par
git).

**Sur un GPU** (celui utilisé ici : ~7 min par enregistrement de 2 h,
dont ~20 s pour l'étape 1). Il suffit d'une carte NVIDIA avec ~6 Go de
mémoire et un PyTorch avec CUDA ; les scripts utilisent le GPU tout seuls
s'il est là.

**Sans GPU à soi**, un GPU loué ou gratuit dans le cloud convient :

- **Google Colab** (gratuit, GPU T4) : *Exécution → Modifier le type
  d'exécution → GPU*, puis dans une cellule :
  ```
  !git clone <ce dépôt> && cd dalail-asr && pip install -r new/requirements.txt
  %cd dalail-asr
  !curl -O https://pub-399f14501bad46a28b40e12c0215d805.r2.dev/hamzia.mp3
  !bash new/run.sh hamzia hamzia.mp3 hamzia_verses.json old/hamzia_labels.txt
  ```
  (ffmpeg est déjà installé sur Colab.) Compter ~15–25 min par
  enregistrement sur un T4. Téléchargez ensuite les fichiers produits à la
  racine (`*_labels.txt`, `*_word_labels.txt`, `*_words.json`).
- **Kaggle Notebooks** (gratuit, GPU) ou **RunPod / Lambda / Vast.ai**
  (quelques centimes l'heure) : mêmes commandes dans un terminal.

**Sur CPU seulement** ça marche aussi, mais lentement : l'étape 1 prend de
l'ordre d'une heure pour 2 h d'audio, l'étape 2 bien davantage. À réserver
à un essai sur un extrait.

### Un nouvel enregistrement

La même commande sert pour n'importe quel enregistrement : seul change le
**nom** que vous lui donnez (il nomme les fichiers produits).

1. **Le texte.** Écrivez-le dans un fichier texte brut, une ligne (ou un
   vers) par rangée, dans l'ordre où il est chanté. Pour un vers en deux
   hémistiches, séparez les deux moitiés par « * ». Mettez entre
   parenthèses les mots que le munshid peut omettre : `(سيدنا)`. Puis :
   ```bash
   python new/text_from_txt.py burda burda.txt burda_text.json
   ```
   Commencez par « # » les rangées que le munshid ne chante pas (titres,
   notes de l'édition) : elles restent dans le texte, marquées
   `"chanted": false`, et ne sont jamais cherchées — sinon, courtes et
   banales, elles peuvent se poser sur l'audio d'une vraie ligne.
   (Vous pouvez aussi écrire directement le JSON : une liste de
   `{"id", "text"}`, plus `"chanted": false` au besoin — c'est le format
   de `hamzia_verses.json`.)
2. **L'audio.** Posez le fichier (mp3, m4a, wav… tout ce que lit ffmpeg)
   à la racine du dépôt, par exemple `burda.mp3`.
3. **Lancer :**
   ```bash
   new/run.sh burda burda.mp3 burda_text.json
   # avec un titre pour les pages de vérification :
   TITLE="البردة" new/run.sh burda burda.mp3 burda_text.json
   ```
   Sans fichier a priori, chaque ligne est cherchée sur ±40 min autour
   d'une position proportionnelle à son rang dans le texte. Si vous
   disposez d'étiquettes Audacity grossières (une par ligne, même placées
   à la main à quelques secondes près), passez-les en 4ᵉ argument : la
   recherche est alors plus sûre et plus rapide.
4. **Les sorties** portent le nom choisi : `burda_labels.txt`,
   `burda_word_labels.txt`, `burda_words.json`. `review_data.js` inclut
   désormais aussi ce nouvel enregistrement. Pour la page mot par mot :
   ```bash
   python new/word_review_data.py && ./word_review.sh
   ```
   Les pages lisent l'audio à la racine du dépôt (`burda.mp3`) ; pour un
   audio en ligne, donnez son URL : `AUDIO_URL=https://… new/run.sh …`.
   Il n'y a pas de timing « ancien » pour un nouvel enregistrement : le
   bouton القديم n'aura rien à montrer.
5. **Écouter les lignes manquantes.** `./review.sh`, puis choisissez
   l'enregistrement — ou ouvrez directement
   `http://localhost:8097/review.html#burda/missing` : seules les lignes
   non placées s'affichent (en violet), et un clic fait entendre l'audio
   entre leurs deux voisines. Trois cas :
   - **on n'y entend rien de cette ligne** (titre, note, ligne sautée) :
     rien à faire — ou, si c'est un titre ou une note, marquez-la « # »
     dans le texte pour qu'elle ne soit plus jamais cherchée ;
   - **elle y est chantée** : reculez les deux voisines d'une ligne ou
     deux dans la page (voir « Corriger les positions ») et signalez-le —
     c'est un cas à étudier ;
   - **elle est chantée ailleurs** (le munshid change l'ordre) : le
     pipeline suit l'ordre du texte ; déplacez la ligne dans le texte à
     l'endroit où elle est chantée.
6. **Relancer après avoir marqué des lignes « # ».** Inutile de tout
   refaire (l'étape 1 est la plus longue) : si le texte a gardé le même
   nombre de lignes, dans le même ordre, seules les étapes 3 bis et 4
   tournent à nouveau, en quelques minutes :
   ```bash
   python new/text_from_txt.py burda burda.txt burda_text.json
   python new/fill_gaps.py new/work/burda.pt burda_text.json \
       new/work/burda_decision.json new/work/burda_candidates.json new/work/burda_final.json
   python new/export.py burda burda_text.json new/work/burda_final.json --audio-file burda.mp3
   ```
   Si des lignes ont été ajoutées, retirées ou déplacées, relancez
   `new/run.sh` en entier.

Si beaucoup de lignes finissent « non chantées », c'est souvent que la
position a priori est trop loin : relancez l'étape 2 avec une fenêtre plus
large (`python new/find_lines.py … --window-min 60`), ou fournissez des
étiquettes a priori.

## Réglages et limites

- **Le blanc et le joker** (`find_lines.py --beta 1.2 --cost 1.0`). Un
  modèle CTC donne le symbole « blanc » à la plupart des trames, même en
  pleine parole ; gratuit, il laisserait égrener les lettres d'une ligne
  sur des minutes. Le blanc coûte donc `beta` par trame et le joker `cost`,
  avec `cost < beta < 4/3·cost`. Ne changez ces valeurs qu'en connaissance
  de cause.
- **Seuils de décision** (`decide.py`) : `REWARD` (au-dessus de quel score
  une ligne est prise), `REPEAT` (quel écart de score admet une
  répétition). `export.py` marque `REVIEW` sous un score de −1,2.
- **Mots optionnels** `(سَيِّدِنَا)` : le choix « chantés / pas chantés »
  est la partie la moins sûre (deux modèles indépendants ne s'accordent
  qu'une fois sur deux). Si le surlignage trébuche autour de ces mots,
  c'est la cause probable.
- **Répétitions** : une répétition n'est retenue que si elle suit sa
  ligne de près (≤ 20 s) — les vraies sont séparées de 2 à 5 s ; au-delà,
  c'est le plus souvent un vers voisin qui lui ressemble (même mètre, même
  rime). Mérite une oreille : Hamziyya v044 (15 s entre les passages,
  peut-être un interlude).
- **Lignes retrouvées dans leur trou** (`found_in_gap`) : placées par la
  seconde passe, dans un espace étroit ; ce sont les premières à écouter.
- Le Dalail reste plus difficile que la Hamziyya (ensemble, interludes,
  ~30 % du texte non chanté dans cet enregistrement) : ses scores sont plus
  bas, et les lignes REVIEW demandent une oreille.

## Vérifier à l'oreille

### Mot par mot — `word_review.html`

```bash
./word_review.sh     # sert ce dossier sur :8532 et ouvre la page
```

Les deux enregistrements, chaque mot allumé quand il est chanté. Le
bouton **الجديد / القديم** bascule entre le nouveau timing et l'ancien
(Whisper) ; les mots pâles n'avaient aucun temps dans l'ancien. Cliquez un
mot pour y amener l'audio ; «×2» signale une ligne chantée deux fois, qui
s'allume à chaque passage. L'audio est diffusé depuis R2.

### Ligne par ligne — `review.html`

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
surligne et suit. **Les lignes orange sont marquées REVIEW** — non
trouvées dans l'audio (intervalle interpolé) ou placées avec une
confiance faible — ce sont elles qui demandent une oreille. L'en-tête
compte تلقائي et للمراجعة. **Les lignes violettes (« غير مُنشَد ») ne
sont pas placées** : leur intervalle est le trou entre leurs voisines,
avec sa durée (« فراغ 12s », ou « لا فراغ بين جارَيه » si les voisines se
touchent), et un clic joue à partir de 3 s avant ce trou. Les filtres
الكل / غير المُنشَد فقط / للمراجعة فقط réduisent la liste ; l'adresse
`review.html#dalail/missing` ouvre directement un enregistrement filtré.
Une ligne coupée par le bord de l'enregistrement porte « مقطوع بطرف
التسجيل ». `review_data.js` vient désormais du nouveau pipeline ; celui
de l'ancien est dans `old/`.

#### Corriger les positions

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
la copie durable. (Les index de ligne sont les mêmes dans l'ancien et le
nouveau `review_data.js` : une ligne du texte = une ligne de la page.)

## L'ancien pipeline (dans `old/`, pour référence)

1. **Transcription** — `old/hamzia_transcribe.py` /
   `old/dalail_transcribe.py`, sur GPU, faster-whisper large-v3 avec
   `vad_filter=False` : le VAD entend la mélodie, décide « musique, pas
   parole », et ne garde presque rien d'une qasida chantée. Sortie :
   `old/*.asr.json` avec horodatage par mot. (Ces deux scripts lisent et
   écrivent dans `~/dalail-lab` : adaptez le chemin `LAB` pour les
   relancer.)
2. **Texte de référence** — `hamzia_verses.json` (les vers de la
   qasida) ; `extract_dalail_segments.py` extrait `dalail_segments.json`
   du JSON embarqué de l'application Dalail.
3. **Alignement** — `old/hamzia_match.py` / `old/dalail_match.py` :
   Needleman-Wunsch en bande sur les deux flux de mots, avec scores
   flous (les déformations de Whisper restent proches du rasm :
   الأمياء≈الأنبياء) et des trous bon marché (interludes et coupures
   font ~40 % de l'audio). Les lignes sans ancre reçoivent des
   intervalles interpolés et un drapeau REVIEW. Sortie :
   `old/*_labels.txt` (étiquettes Audacity) — et les mêmes lignes
   sérialisées dans `old/review_data.js`. Ils se relancent depuis `old/`
   (`cd old && python3 dalail_match.py`) et y réécrivent leurs étiquettes.

Le docstring de `old/hamzia_match.py` consigne pourquoi la v1 (difflib
global) et la v2 (fenêtre glissante) ont échoué. Ses étiquettes servent
aujourd'hui de position a priori au nouveau pipeline.

## Fichiers

| fichier | rôle |
|---|---|
| `*_labels.txt` | étiquettes Audacity, une par ligne (nouveau pipeline) |
| `*_word_labels.txt` | étiquettes Audacity, une par mot (nouveau) |
| `*_words.json` | lignes, passages et mots, en secondes, pour une application |
| `review.html` + `review_data.js` + `review.sh` | vérifier et corriger les lignes |
| `word_review.html` + `word_review_data.js` + `word_review.sh` | vérifier mot par mot, ancien vs nouveau |
| `new/` | le pipeline actuel (alignement forcé CTC) |
| `old/` | l'ancien pipeline (Whisper + appariement) et ses sorties |
| `hamzia_verses.json`, `dalail_segments.json` | textes de référence |
| `extract_dalail_segments.py` | extrait `dalail_segments.json` de l'app Dalail |
| `*.mp3` | les enregistrements (gitignorés ; sur R2) |
