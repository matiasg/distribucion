Cosas que debo hacer
====================

* encuestas
    [-] chequear que en las encuestas no hay opciones repetidas
    [7] chequear que hay la cantidad de opciones correcta
        Esto puede significar que:
          - cada docente tiene pre-fijada una cantidad
          - el docente entra la cantidad de opciones que debe contestar
    [-] Después de una encuesta
        - cambiar el texto!
        - debe decir qué se eligió
    [-] ordenar
        - a los docentes por nombre
        - a los turnos por materia
    [-] - limitar los pesos a 20
    [ ] mandar email después de la respuesta?
    [ ] mandar email con password personalizado?

* materias
    [-] replantear Carga y CuatrimestreDocente.
        - Deben distintos cargos
        - Un cuatrimestre puede ser muy distinto de otro para un mismo docente.
          Por ej., dos cargas de JTP un cuat y dos cargas de Ay1 otro.
        - Que sea fácil pasar de dborrador a distribución definitiva.
    [5] agregar alumnos a los turnos. Agregar una función #alumnos -> necesidades
    [6] página para corregir fácil necesidades

* distribucion
    [4] Página de donde hereden otras como guía
    [-] Avisar de docentes no distribuidos y turnos no cubiertos
    [ ] Historial de un docente
    [4] página para agregar asignaciones fácil para nuevos intentos en dborrador
        Está hecho un poco en la página de ver distribuciones.
    [-] logging en la página cuando hay cargas o necesidades < 0 (hay dos TODO en el código)
    [-] si hay asignaciones previas hay que descontar en los docentes (además de en los turnos)
    [-] si hay encuestas para turnos que no se están distribuyendo, no utilizarlos (y loguear en WARNING)
    [-] en las necesidades, descontar los docentes ya distribuidos
    [-] manejar el campo de "intento"
    [-] borrar todas las asignaciones de un intento antes de distribuir
    [-] normalizar los pesos
    [-] preparar -> distribuir más dinámico

* general
    [3] distintos roles para editar distintas partes
    [3] logs de cambios o forma de hacer restore de estado o medida de seguridad.
    [ ] rol que pueda editar número de alumnos, aula y pab. de un turno.
    [ ] distribucion/settings.py <-- mirar SECRET_KEY >
    [ ] ponerle passwd a la db. Cuando se inicia, tira
        "Use "-e POSTGRES_PASSWORD=password" to set it in "docker run"."
    [-] las cargas son por docente/cuatrimestre
    [-] separar materias según obligatorias/optativas en tools/current_html_to_db.py
    [-] usar postgresql

* hecho
    [-] botón para hacer distribuciones
    [-] armar dockerfile
    [-] las PreferenciasDocente no necesitan año ni cuatrimestre

* charla
    [ ] la gente que tiene dos cargas no debe superponerse en la banda horaria
        Puede ser encuesta con parejas de preferencias
    [ ] juntar turnos chicos para las encuestas (los que son un solo dia)
        Ej: taller de álgebra 1, Matemática 2.
        Propuesta: turnos de docentes != turnos para alumnos.
                    Si hacemos esto, el subnumero es para alumnos y no para docentes.
    [ ] pensar qué hacer con materias repetidas (primer y segundo cuatrimestre). Queremos que se pueda? Que no? Que se intente que no?
    [-] que las preferencias sean editables (no salen en el admin)
    [-] distinguir JTP y ay 1ra
    [-] pre-asignar docentes a materias

Diseño
======
 * cosas que faltan (o que están desparramadas y es momento de juntar)
    - funciones que pasen de TipoDocentes -> Cargo
    - TipoDocentes -> anno -> cuatrimestre -> [docente: cargas]
    - TipoDocentes -> anno -> cuatrimestre -> [turnos]
    - TipoDocentes -> anno -> cuatrimestre -> [turno: necesidad]
    - TipoDocentes -> anno -> cuatrimestre -> intento -> [asignaciones]
    - TipoDocentes -> anno -> cuatrimestre -> intento -> [docente: asignaciones]
