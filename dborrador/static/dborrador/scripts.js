$(document).ready(function(){
  $("button#esconder").click(function(){
    $("#escondible").toggle("blind");
  });
});

$(document).ready(function(){
    $( "#preguntas_distribucion_algoritmo" ).dialog({ autoOpen: false });
    $( "#mandar_a_publicar" ).dialog({ autoOpen: false });
    $( "#cambiar_docente_dialogo" ).dialog({ autoOpen: false });
});
$(document).ready(function(){
    $( ".base_opciones #distribuir" ).click(function() {
        $( "#preguntas_distribucion_algoritmo" ).dialog( "open" );
    });
    $( ".base_opciones #publicar" ).click(function() {
        $( "#mandar_a_publicar" ).dialog( "open" );
    });
    $( "#actuar #cambiar_docente" ).click(function() {
        $( "#cambiar_docente_dialogo" ).dialog( "open" );
        $( "#cambiar_docente_dialogo" ).dialog({
            buttons: [
                {
                    text: 'Sí',
                    click: function() {
                        $("#cambiar_docente").submit();
                    },
                    icons: { primary: 'ui-icon-check' }
                }
            ]
        });
    });
});
