
    
  
        return False

    if response.status_code not in (
        200,
        204,
    ):

        raise RuntimeError(
            "Discord Content konnte "
            "nicht aktualisiert werden.\n"
            f"HTTP {response.status_code}\n"
            f"{response.text}"
        )

    return True


def update_or_create_discord_image(
    state,
    state_key,
    image_file,
    discord_filename,
    label,
):

    message_id = state.get(
        state_key
    )

    if message_id:

        print(
            f"{label} wird aktualisiert ..."
        )

        updated = patch_discord_image(
            message_id,
            image_file,
            discord_filename,
        )

        if updated:

            print(
                f"{label} aktualisiert. "
                f"Message-ID: {message_id}"
            )

            return False

        print(
            f"{label}: gespeicherte "
            "Discord-Nachricht wurde nicht "
            "gefunden. Sie wird neu erstellt."
        )

    else:

        print(
            f"{label}: noch keine "
            "Message-ID gespeichert. "
            "Nachricht wird erstellt ..."
        )

    new_message_id = post_discord_image(
        image_file,
        discord_filename,
    )

    state[state_key] = new_message_id

    print(
        f"{label} erstellt. "
        f"Message-ID: {new_message_id}"
    )

    return True



def update_one_milestone(milestone):
    filename = LAUNCH.save_milestone_card(milestone)
    state = load_message_state()
    key = milestone["key"]
    changed = update_or_create_discord_image(
        state=state,
        state_key=f"{key}_message_id",
        image_file=filename,
        discord_filename=f"{key}.png",
        label=milestone["title"],
    )
    if changed:
        save_message_state(state)


def should_update(milestone, mode, now, timezone_name):
    target = LAUNCH.parse_launch_datetime(milestone["date"], timezone_name)
    remaining = (target - now).total_seconds()
    # Normaler Content-Job bleibt unabhängig vom Countdown aktiv.
    if mode == "daily":
        return True
    # Ein verspäteter Lauf darf das endgültige GESTARTET nicht verpassen.
    # Nach dem Start übernimmt der reguläre tägliche Content-Job.
    if remaining <= 0:
        return mode == "minute" and remaining > -120
    if mode == "quarter":
        return 3600 < remaining <= 86400
    if mode == "minute":
        return remaining <= 3600
    raise ValueError(f"Unbekannter CONTENT_MODE: {mode}")


def main():
    data = load_json(DATA_FILE)
    if not data:
        raise RuntimeError("content_data.json ist leer oder fehlt.")
    mode = os.environ.get("CONTENT_MODE", "daily").strip().lower()
    if mode not in ("daily", "quarter", "minute"):
        raise ValueError(f"Ungültiger CONTENT_MODE: {mode}")
    timezone_name = data.get("timezone", "Europe/Berlin")
    now = datetime.now(ZoneInfo(timezone_name))
    content_state = LAUNCH.build_content_state(data)
    milestones = {m["key"]: m for m in content_state["milestones"]}
    for key in ("early_access", "global_launch"):
        if key not in milestones:
            raise RuntimeError(f"Milestone fehlt in content_data.json: {key}")
    for key in ("early_access", "global_launch"):
        milestone = milestones[key]
        if should_update(milestone, mode, now, timezone_name):
            print(f"{mode}: {milestone['title']} – {milestone['status_text']}")
            update_one_milestone(milestone)
        else:
            print(f"{mode}: {milestone['title']} – außerhalb des Zeitfensters")


if __name__ == "__main__":
    main()

