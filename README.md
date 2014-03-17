RPi-IRTransceiver-WS-Serrver
============================

Cette librairie Python fournie un server websocket qui permet de recevoir et envoyer
des codes infrarouge à l'aide des ports GPIO d'un raspberry.

La librairie utilise les librairies :
* RPi.GPIO (https://pypi.python.org/pypi/RPi.GPIO) modifiée
* BCM2835 (http://www.airspayce.com/mikem/bcm2835/index.html) intégrée dans RPi.GPIO
 
L'utilisation de BCM2835 permet une meilleur gestion du PWM (Pulse With Modulation) pour
l'émission du code infrarouge.

Ce code modifié est disponible ici : https://github.com/Nico0084/RPi-GPIO_BCM2835-IR_TOOLS
Il est à installer comme dépendance en lieu et place de RPi.GPIO.

Pour l'instant il ne travail en PWM que sur le GPIO 18 (Channel 0) et pour une fréquence de 38Khz

Le Raspberry ne permettent pas de contrôle temps réel, le code ne peut garantir l'émission et réception de façon sur.

Il ni a aucune garantie sur le bon fonctionnement.

Installation :
--------------

    git clone http://github.com/Nico0084/RPi-IRTransceiver-WS-Server.git
    cd RPi-IRTransceiver-WS-Server
    sudo python setup.py install

Ajouter le démarrage du serveur au boot :
----------------------------------------

    sudo update-rc.d irtransceiver defaults 99

Démarrage manuel du serveur :
----------------------------

    sudo /etc/init.d/irtransceiver start
ou

    irtransceiver

pour développer un client voir le script `tests/wsclient_test.py` ainsi que l'entête du script `bin/ir_transceiver.py`



