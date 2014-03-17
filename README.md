
Cette librairie Python fournie un server websocket qui permet de recevoir et envoyer
des codes infrarouge � l'aide des ports GPIO d'un raspberry.

La librairie utilise les librairies :
 - RPi.GPIO (https://pypi.python.org/pypi/RPi.GPIO) modifi�e
 - BCM2835 (http://www.airspayce.com/mikem/bcm2835/index.html) int�gr�e dans RPi.GPIO
 
L'utilisation de BCM2835 permet une meilleur gestion du PWM (Pulse With Modulation) pour
l'�mition du code infrarouge.

Ce code modifi� est disponible ici : https://github.com/Nico0084/RPi-GPIO_BCM2835-IR_TOOLS
Il est � installer comme d�pendance en lieu et place de RPi.GPIO.

Pour l'instant il ne travail en PWM que sur le GPIO 18 (Channel 0) et pour une fr�quence de 38Khz

Le Raspberry ne permettent pas de cont�le temps r�el, le code ne peut garantir l'�mission et reception
de fa�on sur.

Il ni a aucune garantie sur le fonctionnement.

Installation :
=============

git clone http://github.com/Nico0084/RPi-IRTransceiver-WS-Server.git
cd RPi-IRTransceiver-WS-Server
sudo python setup.py install

Ajouter le d�marrage du server au boot :
==============================

sudo update-rc.d irtransceiver defaults 99

D�marrage manuel du server :
============================

sudo /etc/init.d/irtransceiver start
ou
irtransceiver

pour develloper un client voir le script tests/wsclient_test.py 
ainsi que l'ent�te du script bin/ir_transceiver.py



