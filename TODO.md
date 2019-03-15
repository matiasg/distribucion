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
    [-] en las necesidades, descontar los docentes ya distribuidos
    [-] manejar el campo de "intento"
    [-] borrar todas las asignaciones de un intento antes de distribuir
    [1] normalizar los pesos

* general
    [ ] distribucion/settings.py <-- mirar SECRET_KEY
    [-] las cargas son por docente/cuatrimestre
    [ ] separar materias según obligatorias/optativas en tools/current_html_to_db.py

* hecho
    [-] botón para hacer distribuciones
    [-] armar dockerfile
    [-] las PreferenciasDocente no necesitan año ni cuatrimestre

* charla
    [-] distinguir JTP y ay 1ra
    [-] pre-asignar docentes a materias
    [ ] la gente que tiene dos cargas no debe superponerse en la banda horaria
        Puede ser encuesta con parejas de preferencias
    [ ] juntar turnos chicos para las encuestas (los que son un solo dia)
        Ej: taller de álgebra 1, Matemática 2.
    [-] que las preferencias sean editables (no salen en el admin)
    [ ] pensar qué hacer con materias repetidas (primer y segundo cuatrimestre). Queremos que se pueda? Que no? Que se intente que no?
