def test_obsidian_link_is_configuration_not_personal_source_constant():
    from data_library.research_view import obsidian_link
    item={'path':'question one.md'}
    assert obsidian_link(item,{}) is None
    link=obsidian_link(item,{'obsidian_vault':'Research Vault','obsidian_inbox':'Approved Inbox'})
    assert link=='obsidian://open?vault=Research%20Vault&file=Approved%20Inbox%2Fquestion%20one.md'
