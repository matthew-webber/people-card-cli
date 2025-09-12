def cmd_show(args, state):
    if not args:
        state.list_variables()
        return
    target = args[0].lower()
    if target == "variables" or target == "vars":
        state.list_variables()
    elif target == "domains":
        if not state.excel_data:
            print("❌ No DSM file loaded. Set DSM_FILE first.")
            return
        print(f"\n📋 Available domains ({len(DOMAINS)}):")
        display_domains()
    elif target == "page" or target == "data":
        if state.current_page_data:
            display_page_data(state.current_page_data)
        else:
            print("❌ No page data loaded. Run 'check' first.")
    elif target == "profile":
        if len(args) < 2:
            print(
                "❌ Missing profile target. Use 'show profile before' or 'show profile after'."
            )
            return
        which = args[1].lower()
        if which not in ("before", "after"):
            print(f"❌ Unknown profile target: {which}")
            print("Available profile targets: before, after")
            return
        file_path = Path("update_provider_profile_urls") / f"{which}.html"
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        try:
            subprocess.run(
                [
                    "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl",
                    str(file_path),
                ],
                check=True,
            )
        except Exception:
            try:
                _open_file_in_default_app(file_path)
            except Exception as e:
                print(f"❌ Failed to open file: {e}")
                return
        print(f"✅ Opening profile {which}: {file_path}")
    else:
        print(f"❌ Unknown show target: {target}")
        print("Available targets: variables, domains, page, profile")
