# Sublime Text 2 : Build Project Tree

Builds entire project tree.

## Using

* Create project directory.
* Create a text file and open it with Sublime.
* Define the project structure.
* Press `ctrl+shift+alt+t` to build the project tree

e.g.
    Hello World/
        index.php
        controllers/
            Default.php
            Greetings.php
        models/
            Greetings.php
        views/
            greetings/
                greet.php

will create following project structure,


    Hello World/index.php
    Hello World/controllers/Default.php
    Hello World/controllers/Greetings.php
    Hello World/models/Greetings.php
    Hello World/views/Greetings.php
    Hello World/views/greetings/greet.php

