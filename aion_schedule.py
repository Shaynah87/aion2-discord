# ============================================================
# RIFT-KARTE
# ============================================================

def create_rift_card(
    rift_data,
    rift_times
):
    image = load_rift_background()

    # Rift wieder kompakter wie vor der letzten Größenänderung
    target_width = 1200
    target_height = 540

    image = crop_and_resize(
        image,
        target_width,
        target_height
    )

    image = add_left_gradient(
        image,
        fade_ratio=0.76,
        max_alpha=235,
        tone=(3, 2, 7)
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA"
    )

    title_font = load_font(
        56,
        bold=True
    )

    subtitle_font = load_font(
        29,
        bold=False
    )

    status_font = load_font(
        31,
        bold=True
    )

    time_font = load_font(
        48,
        bold=True
    )

    secondary_font = load_font(
        30,
        bold=False
    )

    white = (
        250,
        248,
        251,
        255
    )

    red = (
        255,
        78,
        88,
        255
    )

    light_red = (
        255,
        135,
        140,
        255
    )

    secondary_color = (
        225,
        222,
        225,
        255
    )

    # --------------------------------------------------------
    # TITEL
    # --------------------------------------------------------

    draw_text_with_shadow(
        draw,
        (72, 48),
        "SPACETIME RIFT",
        title_font,
        white
    )

    draw_text_with_shadow(
        draw,
        (74, 116),
        (
            f"Alle "
            f"{rift_data['interval_hours']} Stunden"
        ),
        subtitle_font,
        light_red
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if rift_times[
        "active_start"
    ]:

        main_label = "JETZT AKTIV"

        main_start = (
            rift_times[
                "active_start"
            ]
        )

        main_end = (
            rift_times[
                "active_end"
            ]
        )

        secondary_label = "Nächster"

        secondary_start = (
            rift_times[
                "next_start"
            ]
        )

    else:

        main_label = "NÄCHSTER"

        main_start = (
            rift_times[
                "next_start"
            ]
        )

        main_end = (
            main_start +
            timedelta(
                minutes=rift_data[
                    "duration_minutes"
                ]
            )
        )

        secondary_label = "Danach"

        secondary_start = (
            rift_times[
                "following_start"
            ]
        )

    secondary_end = (
        secondary_start +
        timedelta(
            minutes=rift_data[
                "duration_minutes"
            ]
        )
    )

    # --------------------------------------------------------
    # HAUPTSTATUS
    # --------------------------------------------------------

    draw_text_with_shadow(
        draw,
        (74, 190),
        main_label,
        status_font,
        red
    )

    # --------------------------------------------------------
    # HAUPTZEIT
    # --------------------------------------------------------

    main_time_text = format_time_range(
        main_start,
        main_end
    )

    main_time_position = (
        72,
        230
    )

    draw_text_with_shadow(
        draw,
        main_time_position,
        main_time_text,
        time_font,
        white
    )

    main_bbox = draw.textbbox(
        main_time_position,
        main_time_text,
        font=time_font
    )

    secondary_y = (
        main_bbox[3] +
        SECONDARY_GAP
    )

    # --------------------------------------------------------
    # UNTERE ZEILE
    # --------------------------------------------------------

    secondary_text = (
        f"→ {secondary_label}: "
        f"{format_time_range(
            secondary_start,
            secondary_end
        )}"
    )

    draw_text_with_shadow(
        draw,
        (74, secondary_y),
        secondary_text,
        secondary_font,
        secondary_color
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        RIFT_CARD_FILE,
        "PNG",
        optimize=True
    )
