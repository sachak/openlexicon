function collapse_menu(menu) {
    $(menu).next().collapse("hide");
    $(menu).prop('aria-expanded', 'false');
    $(menu).find('.submenu-icon').find('i').removeClass('fa-sort-up');
    $(menu).find('.submenu-icon').find('i').addClass('fa-sort-down');
}

function expand_menu(menu) {
    $(menu).next().collapse("show");
    $(menu).prop('aria-expanded', 'true');
    $(menu).find('.submenu-icon').find('i').removeClass('fa-sort-down');
    $(menu).find('.submenu-icon').find('i').addClass('fa-sort-up');
}

function menu_is_open(menu) {
    return $(menu).prop('aria-expanded') === 'true';
}

function close_menu(menu) {
    collapse_menu(menu);
    localStorage.setItem($(menu).prop('id'), 'collapsed');
}

function open_menu(menu) {
    expand_menu(menu);
    localStorage.setItem($(menu).prop('id'), 'expanded');
    // closing brother menus
    $(menu).parent().parent().children('.nav-menu').children('.nav-menu-text:not(#' + $(menu).attr('id') +')').each(function() {
        close_menu($(this));
    });
}

function menu_click(event) {
    let menu = $(event.target);
    if(!menu.hasClass('nav-menu-text')) {
        // if clicked on the checkbox
        if (menu.hasClass("database-checkbox")){
            return;
        }
        menu = $(menu.parents('.nav-menu-text'));
    }
    if(menu.next().hasClass('collapsing')) {
        // if the menu is currently collapsing
        return false;
    }
    if(menu_is_open(menu)) {
        close_menu(menu);
    } else {
        open_menu(menu);
    }
    return false;
}
