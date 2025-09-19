from commands.show import cmd_show


DOMAINS = [
    {
        "full_name": "Enterprise",
        "worksheet_name": "Enterprise",
        "sitecore_domain_name": "Enterprise",
        "url": "web.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Adult Health",
        "worksheet_name": "Adult Health",
        "sitecore_domain_name": "Health",
        "url": "muschealth.org",
        "worksheet_header_row": 2,
    },
    {
        "full_name": "Education",
        "worksheet_name": "Education",
        "sitecore_domain_name": "Education",
        "url": "education.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Research",
        "worksheet_name": "Research",
        "sitecore_domain_name": "Research",
        "url": "research.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Hollings Cancer",
        "worksheet_name": "Hollings Cancer",
        "aliases": ["Hollings Cancer Center", "HCC"],  # alternative full_name values
        "sitecore_domain_name": "Hollings",
        "url": "hollingscancercenter.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Childrens Health",
        "worksheet_name": "Childrens Health",
        "aliases": ["Children's Health", "Kids"],  # alternative full_name values
        "sitecore_domain_name": "Kids",
        "url": "musckids.org",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CDM",
        "worksheet_name": "CDM",
        "sitecore_domain_name": "Dental Medicine",
        "url": "dentistry.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "MUSC Giving",
        "worksheet_name": "MUSC Giving",
        "sitecore_domain_name": "Giving",
        "url": "giving.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CGS",
        "worksheet_name": "CGS",
        "sitecore_domain_name": "Graduate Studies",
        "url": "gradstudies.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CHP",
        "worksheet_name": "CHP",
        "sitecore_domain_name": "Health Professions",
        "url": "chp.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "COM",
        "worksheet_name": "COM",
        "sitecore_domain_name": "Medicine",
        "url": "medicine.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CON",
        "worksheet_name": "CON",
        "sitecore_domain_name": "Nursing",
        "url": "nursing.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "COP",
        "worksheet_name": "COP",
        "sitecore_domain_name": "Pharmacy",
        "url": "pharmacy.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "News Releases",
        "worksheet_name": "News Releases",
        "sitecore_domain_name": "Content Hub",
        "url": "web.musc.edu/about/leadership/institutional-offices/communications/pamr/news-releases",
        "worksheet_header_row": 0,
        "existing_url_col_name": "Current URL",
        "proposed_url_col_name": "proposed path",
        "root_for_new_sitecore": "Content Hub",
    },
    {
        "full_name": "Progress Notes",
        "worksheet_name": "ProgressNotes",
        "sitecore_domain_name": "Content Hub",
        "aliases": ["ProgressNotes"],  # alternative full_name values
        "url": "muschealth.org/health-professionals/progressnotes",
        "worksheet_header_row": 0,
        "existing_url_col_name": "Current URL",
        "proposed_url_col_name": "proposed path",
        "root_for_new_sitecore": "Content Hub",
    },
]

DOMAIN_MAPPING = {
    domain["url"]: domain["sitecore_domain_name"] for domain in DOMAINS if domain["url"]
}


def get_commands(state):
    """Build a minimal mapping of command names to handlers."""
    from commands.report import cmd_report
    from commands.common import cmd_help
    from commands.bulk import cmd_bulk_check
    from commands.scan import cmd_scan
    from commands.extract import cmd_extract
    from commands.core import cmd_open
    from commands.history import cmd_history

    return {
        "bulk_check": lambda args: cmd_bulk_check(args, state),
        "bulk": lambda args: cmd_bulk_check(args, state),  # Alias for bulk
        "scan": lambda args: cmd_scan(args, state),
        "extract": lambda args: cmd_extract(args, state),
        "report": lambda args: cmd_report(args, state),
        "show": lambda args: cmd_show(args, state),
        "open": lambda args: cmd_open(args, state),
        "help": lambda args: cmd_help(args, state),
        "history": lambda args: cmd_history(args, state),
        "exit": lambda args: exit(0),
        "quit": lambda args: exit(0),
        "q": lambda args: exit(0),
    }
