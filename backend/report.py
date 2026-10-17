from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import StoredSession


def build_pdf(session: StoredSession) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Ek Awaaz incident {session.incident.session_id[:8]}",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleWarm", parent=styles["Title"], textColor=colors.HexColor("#1F1B16"), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="SmallMuted", parent=styles["BodyText"], fontSize=8, textColor=colors.HexColor("#6B635A")))
    incident = session.incident
    story = [
        Paragraph("Ek Awaaz — Incident report", styles["TitleWarm"]),
        Paragraph("DEMO MODE — test contacts only" if session.demo_mode else "Configured stand-in contacts only", styles["SmallMuted"]),
        Spacer(1, 7 * mm),
    ]
    facts = [
        ["Session", incident.session_id],
        ["Started", session.started_at.isoformat()],
        ["Ended", session.ended_at.isoformat() if session.ended_at else "Active"],
        ["Type", incident.type.replace("_", " ").title()],
        ["Location", incident.location.text or "Not captured"],
        ["People / injured", f"{incident.people.count} / {incident.people.injured}"],
        ["Severity", incident.severity.title()],
        ["Hazards", ", ".join(incident.hazards) or "None reported"],
        ["Confirmed", "Yes" if incident.dispatch_confirmed else "No"],
    ]
    table = Table(facts, colWidths=[40 * mm, 120 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FBF7F2")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F1B16")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EADFD3")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([table, Spacer(1, 7 * mm), Paragraph("Who we contacted", styles["Heading2"])])
    if incident.actions:
        action_rows = [["Time", "Kind", "Target", "Status", "Summary"]]
        action_rows.extend([
            [a.ts.strftime("%H:%M:%S"), a.kind, a.target, a.status, Paragraph(a.script_summary, styles["SmallMuted"])]
            for a in incident.actions
        ])
        actions = Table(action_rows, repeatRows=1, colWidths=[20 * mm, 16 * mm, 31 * mm, 20 * mm, 73 * mm])
        actions.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4572E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#EADFD3")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(actions)
    else:
        story.append(Paragraph("No contact actions recorded.", styles["BodyText"]))
    story.extend([Spacer(1, 7 * mm), Paragraph("Transcript", styles["Heading2"])])
    for item in incident.transcript:
        label = "Caller" if item.speaker == "caller" else "Listener"
        story.append(Paragraph(f"<b>{label} · {item.ts.strftime('%H:%M:%S')}</b> — {item.text}", styles["BodyText"]))
        story.append(Spacer(1, 2 * mm))
    document.build(story)
    return output.getvalue()
