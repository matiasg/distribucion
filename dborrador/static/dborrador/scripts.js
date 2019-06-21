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
