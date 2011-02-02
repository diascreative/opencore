
(function($){

$(document).ready(function() {

    $('.mceEditor').tinysafe({
        theme: 'advanced',
        height: '400',
        width: '550',
        gecko_spellcheck : false,
        theme_advanced_toolbar_location: 'top',
        theme_advanced_buttons1: 'formatselect, bold, italic, bullist, numlist, link, code, removeformat, justifycenter, justifyleft,justifyright, justifyfull, indent, outdent, kaltura',
        theme_advanced_buttons2: '',
        theme_advanced_buttons3: '',
        plugins: 'kaltura',
        extended_valid_elements: "object[classid|codebase|width|height],param[name|value],embed[quality|type|pluginspage|width|height|src|wmode|swliveconnect|allowscriptaccess|allowfullscreen|seamlesstabbing|name|base|flashvars|flashVars|bgcolor],script[src]",
        forced_root_block : 'p',
        //options for kaltura
        kaltura_partner_id: '333261',
        kaltura_sub_partner_id: '33326100',
        kaltura_user_secret: 'put_user_secret_here',
        kaltura_admin_secret: 'put_admin_secret_here',
        kaltura_kcw_uiconf_id: '1000741',
        kaltura_player_uiconf_id: '1913582',
        kaltura_player_cache_st: '1286785355'
    });

    $('.preview-button').click(function() {
        // insert into preview area
        $('#preview-area')
            .empty()
            .append(tinymce.activeEditor.getContent());
    });

});

})(jQuery);

