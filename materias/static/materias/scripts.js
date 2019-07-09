$(document).ready(function(){
    $( ".borrar_turno_dialogo" ).dialog({ autoOpen: false });
    $( ".borrar_horario_dialogo" ).dialog({ autoOpen: false });
});
$(document).ready(function(){
    $( "#administrar_materia #borrar_turno" ).click(function() {
        var boton = $(this)[0]
        var turno = boton.getAttribute('data-turno');
        $( ".borrar_turno_dialogo" ).dialog("open");
        $( ".borrar_turno_dialogo" ).dialog({
            buttons: [
                {
                    text: 'Sí',
                    click: function() {
                        url = $(".borrar_turno_dialogo")[0].getAttribute('url').replace('31415926535', turno);
                        window.location = url;
                    },
                    icons: { primary: 'ui-icon-check' }
                }
            ]
        })
    });
    $( "#administrar_materia #borrar_horario" ).click(function() {
        var boton = $(this)[0]
        var horario = boton.getAttribute('data-horario');
        $( ".borrar_horario_dialogo" ).dialog("open");
        $( ".borrar_horario_dialogo" ).dialog({
            buttons: [
                {
                    text: 'Sí',
                    click: function() {
                        url = $(".borrar_horario_dialogo")[0].getAttribute('url').replace('31415926535', horario);
                        window.location = url;
                    },
                    icons: { primary: 'ui-icon-check' }
                }
            ]
        })
    });
});
