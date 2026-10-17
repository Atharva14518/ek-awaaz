from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "deliverables" / "video" / "fonts"
OUTPUT = ROOT / "deliverables" / "ek-awaaz-agentic-ai-proposal.pdf"

pdfmetrics.registerFont(TTFont("Poppins", str(FONT_DIR / "Poppins-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Poppins-Medium", str(FONT_DIR / "Poppins-Medium.ttf")))
pdfmetrics.registerFont(TTFont("Poppins-SemiBold", str(FONT_DIR / "Poppins-SemiBold.ttf")))


INK = colors.HexColor("#18232B")
MUTED = colors.HexColor("#52636B")
TEAL = colors.HexColor("#087F8C")
TEAL_DARK = colors.HexColor("#075C67")
MINT = colors.HexColor("#E7F5F3")
PALE = colors.HexColor("#F5F8F8")
GOLD = colors.HexColor("#F2B84B")
LINE = colors.HexColor("#D7E3E3")
WHITE = colors.white


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="BodyPoppins",
        parent=styles["BodyText"],
        fontName="Poppins",
        fontSize=8.7,
        leading=13.2,
        textColor=INK,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallPoppins",
        parent=styles["BodyText"],
        fontName="Poppins",
        fontSize=7.3,
        leading=10.3,
        textColor=MUTED,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletPoppins",
        parent=styles["BodyText"],
        fontName="Poppins",
        fontSize=8.25,
        leading=11.7,
        leftIndent=12,
        firstLineIndent=-8,
        bulletIndent=0,
        textColor=INK,
        spaceAfter=3.2,
    )
)
styles.add(
    ParagraphStyle(
        name="SectionPoppins",
        parent=styles["Heading2"],
        fontName="Poppins-SemiBold",
        fontSize=13.2,
        leading=16,
        textColor=TEAL_DARK,
        spaceBefore=6,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="SubheadPoppins",
        parent=styles["Heading3"],
        fontName="Poppins-SemiBold",
        fontSize=9.5,
        leading=12,
        textColor=INK,
        spaceBefore=3,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="TitlePoppins",
        parent=styles["Title"],
        fontName="Poppins-SemiBold",
        fontSize=28,
        leading=31,
        alignment=TA_LEFT,
        textColor=WHITE,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="SubtitlePoppins",
        parent=styles["BodyText"],
        fontName="Poppins",
        fontSize=10.2,
        leading=14,
        textColor=colors.HexColor("#D8F4F1"),
    )
)
styles.add(
    ParagraphStyle(
        name="LabelPoppins",
        parent=styles["BodyText"],
        fontName="Poppins-SemiBold",
        fontSize=7.1,
        leading=9,
        textColor=TEAL_DARK,
        uppercase=True,
    )
)
styles.add(
    ParagraphStyle(
        name="QuotePoppins",
        parent=styles["BodyText"],
        fontName="Poppins-Medium",
        fontSize=10.1,
        leading=15,
        textColor=TEAL_DARK,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="LinkPoppins",
        parent=styles["BodyText"],
        fontName="Poppins",
        fontSize=7.6,
        leading=10.3,
        textColor=TEAL_DARK,
    )
)


def P(text: str, style: str = "BodyPoppins") -> Paragraph:
    return Paragraph(text, styles[style])


def bullets(items: list[str]) -> list[Paragraph]:
    return [P(f"• {item}", "BulletPoppins") for item in items]


def section(title: str) -> Paragraph:
    return P(title, "SectionPoppins")


def footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Poppins", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "EK AWAAZ  /  TEAM MENTALIST  /  AGENTIC AI PROPOSAL")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"{doc.page} / 3")
    canvas.restoreState()


def hero() -> Table:
    content = [
        P("EK AWAAZ", "TitlePoppins"),
        P("A safety-focused multilingual voice agent for emergency coordination", "SubtitlePoppins"),
        Spacer(1, 7),
        P("AGENTIC AI  ·  ROUND 1 PROPOSAL", "LabelPoppins"),
    ]
    table = Table([[content]], colWidths=[174 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL_DARK),
                ("BOX", (0, 0), (-1, -1), 0, TEAL_DARK),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 13),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
            ]
        )
    )
    return table


def info_table() -> Table:
    rows = [
        [P("TEAM", "LabelPoppins"), P("Team Mentalist", "BodyPoppins")],
        [P("MEMBERS", "LabelPoppins"), P("Atharv Bacchewar  ·  Ayush Wable", "BodyPoppins")],
        [P("SELECTED TRACK", "LabelPoppins"), P("Agentic AI", "BodyPoppins")],
        [P("PROJECT TYPE", "LabelPoppins"), P("Voice-first emergency coordination demo", "BodyPoppins")],
    ]
    table = Table(rows, colWidths=[34 * mm, 140 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def callout(text: str) -> Table:
    table = Table([[P(text, "QuotePoppins")]], colWidths=[174 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), MINT),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#B7E1DC")),
                ("LINEBEFORE", (0, 0), (0, -1), 4, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def two_column(left: list, right: list) -> Table:
    table = Table([[left, right]], colWidths=[85 * mm, 85 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def link(label: str, url: str) -> Paragraph:
    return P(f'<link href="{url}" color="#075C67"><u>{label}</u></link>', "LinkPoppins")


def build_story() -> list:
    story = [
        hero(),
        Spacer(1, 8),
        info_table(),
        Spacer(1, 8),
        callout(
            "Ek Awaaz turns a multilingual emergency conversation into a structured, caller-confirmed incident and coordinates observable response actions through voice, SMS, and location sharing."
        ),
        Spacer(1, 5),
        section("1. Problem Statement & Motivation"),
        P(
            "During an emergency, a caller may need to explain what happened, correct incomplete details, share a location, and contact several people while under stress. A voice conversation alone does not reliably create a verified incident or a coordinated action plan. This gap becomes more important when the caller speaks in Hindi, Hinglish, Marathi, or English—or cannot safely speak at all."
        ),
        P(
            "Ek Awaaz addresses this problem with a human-confirmed agentic workflow: it listens, structures the situation, exposes uncertainty, asks for confirmation, and only then coordinates configured response actions."
        ),
        section("2. Target Users & Intended Use Cases"),
        two_column(
            bullets([
                "A caller reporting an accident, medical emergency, hazard, or unsafe situation.",
                "Trusted family contacts and configured responder stand-ins receiving updates.",
            ]),
            bullets([
                "An operator monitoring the live console, confidence, corrections, and action status.",
                "Judges and evaluators running deterministic spoken and silent-mode demos.",
            ]),
        ),
        section("3. Proposed Solution & Key Features"),
        *bullets([
            "Multilingual voice-first intake with rules-first extraction and optional Groq structured extraction.",
            "Correction-aware incident facts for location, injuries, hazards, landmarks, and urgency.",
            "Explicit caller confirmation before any dispatch action; material corrections reset confirmation.",
            "LangGraph-based planning with parallel, observable actions and bounded retries.",
            "Bolna voice calls, mock-by-default SMS, optional Twilio SMS, and browser GPS sharing.",
            "Silent DTMF mode, WebSocket live console, searchable reports, and downloadable PDF summaries.",
        ]),
        PageBreak(),
        section("4. Technical Approach"),
        P(
            "Ek Awaaz uses one shared orchestration path for simulator, manual transcript, and Bolna webhook input. Incident state and event history are persisted so the operator can see what the agent understood, what changed, and which actions were attempted."
        ),
        callout(
            "Caller / simulator  ->  FastAPI transcript intake  ->  rules + optional Groq extraction  ->  SQLite incident state  ->  confirmation gate  ->  LangGraph dispatcher  ->  Bolna stand-in calls / mock-or-Twilio SMS  ->  React console + report"
        ),
        Spacer(1, 5),
        P("Technology stack", "SubheadPoppins"),
        Table(
            [
                [P("Layer", "LabelPoppins"), P("Tools / implementation", "LabelPoppins")],
                [P("Interface", "SmallPoppins"), P("React, Vite, WebSockets, responsive operations console", "SmallPoppins")],
                [P("Backend", "SmallPoppins"), P("Python 3.11.9, FastAPI, SQLite, Pydantic, ReportLab", "SmallPoppins")],
                [P("Agentic workflow", "SmallPoppins"), P("LangGraph state machine, confirmation gate, parallel dispatch, retries, kill switch", "SmallPoppins")],
                [P("AI and integrations", "SmallPoppins"), P("Optional Groq extraction, Bolna voice API/webhooks, optional Twilio SMS", "SmallPoppins")],
                [P("Reproducibility", "SmallPoppins"), P("Pinned runtimes, npm lockfile, hash-pinned Python lockfile, Docker, make test", "SmallPoppins")],
            ],
            colWidths=[36 * mm, 138 * mm],
        ),
        Spacer(1, 8),
        section("5. How the Agent Acts"),
        *bullets([
            "Perceive: receive natural speech, transcript turns, DTMF input, or browser location.",
            "Structure: extract incident facts and confidence; retain correction history.",
            "Reason: check completeness and plan tailored actions using stateful LangGraph orchestration.",
            "Authorize: ask the caller to confirm the interpreted incident before side effects.",
            "Execute: run allowlisted voice/SMS actions with status events, rate limits, and retry bounds.",
            "Account: persist an event timeline and generate an operator-readable report.",
        ]),
        section("6. Feasibility & Implementation Plan"),
        two_column(
            [
                P("Prototype already demonstrated", "SubheadPoppins"),
                *bullets([
                    "Deterministic accident demo with a location correction.",
                    "Silent medical-emergency DTMF demo.",
                    "Live WebSocket console and PDF report generation.",
                    "Mock-safe actions, confirmation gating, and emergency-number blocking.",
                ]),
            ],
            [
                P("Next implementation steps", "SubheadPoppins"),
                *bullets([
                    "Harden multilingual scenarios and low-confidence failure states.",
                    "Validate provider webhooks and idempotency with owned stand-in numbers.",
                    "Add privacy retention, access control, and structured audit logs.",
                    "For production scale, migrate SQLite events to a durable multi-instance store and queue.",
                ]),
            ],
        ),
        PageBreak(),
        section("7. Innovation & Differentiation"),
        P(
            "The project demonstrates controlled agency rather than an opaque chatbot. Its distinctive value is the complete loop from conversation to verified state to observable action:"
        ),
        *bullets([
            "Confirmation is a first-class authorization boundary, not a final UI prompt.",
            "A material correction invalidates earlier confirmation, reducing stale-action risk.",
            "Side effects are kept outside graph nodes so safety controls remain centralized.",
            "Spoken and silent interaction modes support different emergency constraints.",
            "The action timeline makes every interpretation, correction, retry, and cancellation inspectable.",
            "Provider adapters keep the orchestration layer portable across simulator, manual, and live inputs.",
        ]),
        section("8. Expected Impact & Scalability"),
        two_column(
            [
                P("Expected impact", "SubheadPoppins"),
                *bullets([
                    "Reduce the cognitive burden on a caller under stress.",
                    "Make multilingual emergency intake more structured and reviewable.",
                    "Help one caller coordinate multiple trusted contacts.",
                    "Create an auditable record for follow-up and evaluation.",
                ]),
            ],
            [
                P("Scalability path", "SubheadPoppins"),
                *bullets([
                    "Keep provider integrations behind adapters and preserve one shared agent workflow.",
                    "Replace local SQLite with a durable store and queue for multi-instance operation.",
                    "Add idempotent callbacks, observability, privacy controls, and supervised pilot testing.",
                    "Extend integrations only after safety and regional requirements are validated.",
                ]),
            ],
        ),
        section("9. Prototype & Submission Links"),
        Table(
            [
                [P("GitHub repository", "LabelPoppins"), link("github.com/Atharva14518/ek-awaaz", "https://github.com/Atharva14518/ek-awaaz")],
                [P("Demo video", "LabelPoppins"), link("Open the recorded demo on Google Drive", "https://drive.google.com/drive/folders/1bDC1YSrRfBuHhtaKRmKA6LXoxCal8Fax?usp=sharing")],
            ],
            colWidths=[36 * mm, 138 * mm],
        ),
        Spacer(1, 7),
        P("Safety-by-design", "SubheadPoppins"),
        P(
            "The prototype is demo-safe by default: external actions are simulated, real actions require independent safety switches and explicit confirmation, recipients are allowlisted, and Indian emergency numbers are blocked. Ek Awaaz is positioned as a supervised coordination layer—not a replacement for emergency services."
        ),
        Spacer(1, 4),
        KeepTogether(
            [
                callout(
                    "Proposal thesis: Agentic AI can do more than transcribe an emergency call—it can build situational understanding, ask for confirmation, plan coordinated actions, expose its state to operators, and preserve an accountable record."
                )
            ]
        ),
    ]
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=19 * mm,
        title="Ek Awaaz - Agentic AI Track Proposal",
        author="Team Mentalist",
        subject="Round 1 Hackathon Proposal",
    )
    document.build(build_story(), onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
