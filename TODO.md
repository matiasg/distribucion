Cosas que debo hacer
====================

* encuestas
    [1] chequear que en las encuestas no hay opciones repetidas
    [3] chequear que hay la cantidad de opciones correcta
        Esto puede significar que:
          - cada docente tiene pre-fijada una cantidad
          - el docente entra la cantidad de opciones que debe contestar
    [-] Después de una encuesta
        - cambiar el texto!
        - debe decir qué se eligió
    [ ] mandar email después de la respuesta?
    [ ] mandar email con password personalizado?

* distribucion
    [ ] preparar -> distribuir más dinámico
    [2] en las necesidades, descontar los docentes ya distribuidos
    [-] manejar el campo de "intento"
    [-] borrar todas las asignaciones de un intento antes de distribuir
    [ ] normalizar los pesos

* general
    [ ] distribucion/settings.py <-- mirar SECRET_KEY
    [-] las cargas son por docente/cuatrimestre
    [ ] separar materias según obligatorias/optativas en tools/current_html_to_db.py

* hecho
    [-] botón para hacer distribuciones
    [-] armar dockerfile
    [-] las PreferenciasDocente no necesitan año ni cuatrimestre
