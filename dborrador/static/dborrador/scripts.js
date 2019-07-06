$(document).ready(function(){
  $("button#esconder").click(function(){
    $("#escondible").toggle("blind");
  });
});

$(document).ready(function(){
    $( "#preguntas_distribucion_algoritmo" ).dialog({ autoOpen: false });
    $( "#mandar_a_publicar" ).dialog({ autoOpen: false });
});
$(document).ready(function(){
    $( ".base_opciones #distribuir" ).click(function() {
        $( "#preguntas_distribucion_algoritmo" ).dialog( "open" );
    });
    $( ".base_opciones #publicar" ).click(function() {
        $( "#mandar_a_publicar" ).dialog( "open" );
    });
});

$(document).ready(function(){
    $( ".borrar_turno_dialogo" ).dialog({ autoOpen: false });
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
});
