__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)


from lxml.etree import _Element


__all__ = ['is_child', 'is_descendant', 'is_first_child', 'is_only_child', 
           'is_only_descendant', 'is_first_only_descendant']


def is_child(el, target_el=None):
    'Determine whether an element `el` is the child of `target_el`'
    if target_el is None:
        return True
    return el.getparent() is target_el


def is_descendant(el, target_el=None):
    'Determine whether an element `el` is the descendant of `target_el`'
    if target_el is None:
        return True
    el = el.getparent()
    while el is not None:
        if el is target_el:
            return True
        el = el.getparent()
    return False


def is_first_child(
    el,
    target_el=None,
    consider_text_sibings=True,
    consider_only_elementbase=False,
):
    '''Determine whether an element `el` is the first child of 
    its parent (if any). 
    If `target_el` is specified, then `target_el` must be the parent 
    element of `el`'''
    pel = el.getparent()
    if target_el is None:
        if pel is None:
            return True
    elif pel is not target_el:
        return False

    if consider_only_elementbase:
        cels = el.xpath('preceding-sibling::node()')
        return sum(isinstance(cel, _Element) for cel in cels) > 1
    if consider_text_sibings:
        pred_text = el.xpath('preceding-sibling::text()[1]')
        if pred_text and pred_text[0].strip():
            return False
    return pel[0] is el


def is_only_child(
    el, 
    target_el=None,
    consider_text_sibings=True,
    consider_only_elementbase=False,
):
    '''Determine whether an element `el` is the only child of 
    its parent (if any). 
    If `target_el` is specified, then `target_el` must be the parent 
    element of `el`'''
    pel = el.getparent()
    if target_el is None:
        if pel is None:
            return True
    elif pel is not target_el:
        return False

    if consider_only_elementbase:
        cels = pel.xpath('child::node()')
        return sum(
                isinstance(cel, _Element) for cel in cels
               ) - isinstance(el, _Element) == 0
    if len(pel) > 1:
        return False
    if consider_text_sibings:
        pred_text = el.xpath('preceding-sibling::text()[1]')
        if pred_text and pred_text[0].strip():
            return False
        folw_text = el.xpath('following-sibling::text()[1]')
        if folw_text and folw_text[0].strip():
            return False
    return True


def is_only_descendant(
    el, 
    target_el=None,
    consider_text_sibings=True,
    consider_only_elementbase=False,
    max_depth=None,
):
    '''Determine whether an element `el` has ancestor element `target_el` 
    (could be None, means automatic adaptation), 
    and all descendant elements of `target_el` up to `el` are "only child".
    If `target_el` is specified, then `target_el` must be the ancestor 
    element of `el`'''
    if max_depth is None:
        while is_only_child(el, target_el, 
                            consider_text_sibings, 
                            consider_only_elementbase):
            pel = el.getparent()
            if pel is target_el:
                return True
            el = pel
    else:
        while max_depth > 0 and is_only_child(el, target_el, 
                                              consider_text_sibings, 
                                              consider_only_elementbase):
            pel = el.getparent()
            if pel is target_el:
                return True
            el = pel
            max_depth -= 1

    return False


def is_first_only_descendant(
    el, 
    target_el=None,
    consider_text_sibings=True,
    consider_only_elementbase=False,
    max_depth=None,
):
    '''Determine whether an element `el` has ancestor element `target_el` 
    (could be None, means automatic adaptation), and the child of the 
    "first child" of `target_el` (if any) up to `el` are "only child".
    If `target_el` is specified, then `target_el` must be the ancestor 
    element of `el`'''
    if max_depth is None:
        while is_only_child(el, target_el, 
                            consider_text_sibings, 
                            consider_only_elementbase):
            pel = el.getparent()
            if pel is target_el:
                return True
            el = pel
    else:
        while max_depth > 0 and is_only_child(el, target_el, 
                                              consider_text_sibings, 
                                              consider_only_elementbase):
            pel = el.getparent()
            if pel is target_el:
                return True
            el = pel
            max_depth -= 1

    return is_first_child(el, target_el, 
                          consider_text_sibings, 
                          consider_only_elementbase)



