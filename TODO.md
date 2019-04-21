Cosas que debo hacer
====================

* encuestas
    [13] juntar turnos chicos para las encuestas (los que son un solo dia) (#21)
        Ej: taller de álgebra 1, Matemática 2.
        Propuesta: turnos de docentes != turnos para alumnos.
                    Si hacemos esto, el subnumero es para alumnos y no para docentes.
    [12] Distinguir lista corta y lista larga en encuestas. (#20)
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
    [5] agregar cantidad de alumnos a los turnos. Agregar una función #alumnos -> necesidades (#11)
    [6] página para corregir fácil necesidades (#12)
    [7] borrar CuatrimestreDocente (chequear que realmente no lo usamos) (#13)

* distribucion
    [9] Repartir los docentes que sobran de una distribución en la categoría siguiente. (#15)
    [8] Agregar comentarios en dborrador. (#14)
    [-] Página de donde hereden otras como guía (#6)
    [-] Avisar de docentes no distribuidos y turnos no cubiertos
    [ ] Historial de un docente
    [4] página para agregar asignaciones fácil para nuevos intentos en dborrador (#7)
        - Poder fijar y desfijar docentes de manera fácil en dborrador.
        - Poder fijar para todos los intentos. Agregar botones para eso.
    [10] link para pasar de dborrador/asignacion a materias/carga. (#16)
    [11] Tooltip sobre docentes distribuidos con sus otras opciones. (#17)
    [-] logging en la página cuando hay cargas o necesidades < 0 (hay dos TODO en el código)
    [-] si hay asignaciones previas hay que descontar en los docentes (además de en los turnos)
    [-] si hay encuestas para turnos que no se están distribuyendo, no utilizarlos (y loguear en WARNING)
    [-] en las necesidades, descontar los docentes ya distribuidos
    [-] manejar el campo de "intento"
    [-] borrar todas las asignaciones de un intento antes de distribuir
    [-] normalizar los pesos
    [-] preparar -> distribuir más dinámico

* general
    [-] distintos roles para editar distintas partes (#4)
    [-] logs de cambios o forma de hacer restore de estado o medida de seguridad. (#5)
    [-] rol que pueda editar número de alumnos, aula y pab. de un turno.
    [ ] distribucion/settings.py <-- mirar SECRET_KEY > (#18)
    [ ] ponerle passwd a la db. Cuando se inicia, tira (#19)
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
    [ ] pensar qué hacer con materias repetidas (primer y segundo cuatrimestre).
        Queremos que se pueda? Que no? Que se intente que no?
    [-] que las preferencias sean editables (no salen en el admin)
    [-] distinguir JTP y ay 1ra
    [-] pre-asignar docentes a materias

Diseño
======
 * cosas que faltan (o que están desparramadas y es momento de juntar)
    [-] funciones que pasen de TipoDocentes -> Cargo
    [-] TipoDocentes -> anno -> cuatrimestre -> [docente: cargas]
    [-] TipoDocentes -> anno -> cuatrimestre -> [turnos]
    [-] TipoDocentes -> anno -> cuatrimestre -> [turno: necesidad]
    [-] TipoDocentes -> anno -> cuatrimestre -> intento -> [asignaciones]
    [-] TipoDocentes -> anno -> cuatrimestre -> intento -> [docente: asignaciones]
