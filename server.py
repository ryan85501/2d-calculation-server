def update_html(updates: dict = None, update_date=None, new_result=None, period=None):
    updates = updates or {}
    try:
        html = load_html()
    except Exception as e:
        print(f"❌ Could not load HTML: {e}")
        return

    soup = BeautifulSoup(html, "html.parser")

    # --- Update number blocks (safe, text only) ---
    for key, value in updates.items():
        target = soup.find("div", {"data-id": key})
        if target is not None:
            target.clear()        # clear existing text
            target.append(str(value))  # insert new text only

    # --- Update current date ---
    if update_date:
        date_span = soup.find("span", {"id": "current-date"})
        if date_span:
            date_span.clear()
            date_span.append(update_date)

    # --- Update history table ---
    if new_result and period in ["am", "pm"]:
        table_body = soup.find("tbody", {"id": "history-table-body"})
        if table_body:
            new_row = soup.new_tag("tr")
            date_td = soup.new_tag("td")
            date_td.string = datetime.now(yangon_tz).strftime("%d-%m-%Y")
            am_td = soup.new_tag("td")
            am_td.string = new_result if period == "am" else "--"
            pm_td = soup.new_tag("td")
            pm_td.string = new_result if period == "pm" else "--"
            new_row.extend([date_td, am_td, pm_td])
            table_body.insert(0, new_row)  # prepend row

    # --- Update previous results (calendar view) ---
    if new_result and len(new_result) == 4:
        prev_container = soup.find("div", {"id": "previous-results-container"})
        if prev_container:
            new_div = soup.new_tag("div", **{"class": "results-row text-4xl font-bold font-serif"})
            num_group = soup.new_tag("div", **{"class": "number-group"})
            for digit in new_result:
                span = soup.new_tag("span", **{"class": "digit-span cursor-pointer p-1 rounded-md"})
                span.string = digit
                num_group.append(span)
            new_div.append(num_group)
            prev_container.append(new_div)  # append to bottom

    save_html(str(soup))
    commit_and_push()
