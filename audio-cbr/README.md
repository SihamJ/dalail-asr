# audio-cbr/

Copies à débit constant (CBR) des enregistrements dont l'original est à
débit variable — aujourd'hui `dalail-nourach.mp3`. Même son, au
millième de seconde (vérifié) ; seul le saut à un instant devient exact.
Les mp3 ne sont pas dans git (voir `.gitignore`) :

    ffmpeg -i dalail-nourach.mp3 -map 0:a -c:a libmp3lame -b:a 256k -ar 44100 audio-cbr/dalail-nourach.mp3

`review.sh` et `word_review.sh` s'en servent d'eux-mêmes. Voir le README
racine, « L'audio de Nourach ».
