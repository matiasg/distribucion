$(document).ready(function(){
    $( ".borrar_habilitacion_dialogo" ).dialog({ autoOpen: false });
    $( "button#borrar_habilitacion" ).click(function() {
        var boton = $(this)[0]
        var habi = boton.getAttribute('data-habilitacion');
        $( ".borrar_habilitacion_dialogo" ).dialog("open");
        $( ".borrar_habilitacion_dialogo" ).dialog({
            buttons: [
                {
                    text: 'Sí',
                    click: function() {
                        url = $(".borrar_habilitacion_dialogo")[0].getAttribute('url').replace('31415926535', habi);
                        window.location = url;
                    },
                    icons: { primary: 'ui-icon-check' }
                }
            ]
        })
    });
});
$(document).ready(function(){
    try {
        $(".datepicker").datetimepicker({
            format: "d/m/Y H:i",
        });
    } catch {
    }
});
