from __future__ import annotations

import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import Client, create_client


def running_inside_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__" and not running_inside_streamlit():
    script_path = Path(__file__).resolve()
    print("Iniciando o aplicativo com Streamlit...")
    print("Se o navegador nao abrir automaticamente, acesse: http://localhost:8501")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(script_path),
            "--server.port",
            "8501",
        ],
        check=False,
    )
    sys.exit()


st.set_page_config(page_title="Registro Clinico", page_icon="RC", layout="wide")


TABLES = ["patients", "doctors", "conditions", "medications", "exams", "visits"]


def secret(path: str, default: str = "") -> str:
    current: Any = st.secrets
    for part in path.split("."):
        try:
            current = current[part]
        except Exception:
            return default
    return str(current or default)


@st.cache_resource
def supabase_client() -> Client | None:
    url = secret("supabase.url")
    key = secret("supabase.key")
    if not url or not key or "SEU-PROJETO" in url or "SUA_SUPABASE" in key:
        return None
    return create_client(url, key)


@st.cache_data(ttl=20, show_spinner=False)
def fetch_table(table: str) -> pd.DataFrame:
    client = supabase_client()
    if client is None:
        return pd.DataFrame()
    response = client.table(table).select("*").execute()
    return pd.DataFrame(response.data or [])


def insert_row(table: str, payload: dict[str, Any]) -> None:
    client = supabase_client()
    if client is None:
        st.error("Configure o Supabase em .streamlit/secrets.toml antes de salvar dados.")
        return
    clean = {
        key: (value.isoformat() if isinstance(value, (date, datetime)) else value)
        for key, value in payload.items()
        if value not in ("", None)
    }
    client.table(table).insert(clean).execute()
    st.cache_data.clear()
    st.success("Registro salvo.")


def optional_date_input(label: str, key: str, container: Any = st) -> date | None:
    has_date = container.checkbox(f"Informar {label.lower()}", key=f"{key}_enabled")
    if not has_date:
        return None
    return container.date_input(label, value=date.today(), key=key)


def optional_number_input(label: str, key: str, container: Any = st) -> float | None:
    has_value = container.checkbox(f"Informar {label.lower()}", key=f"{key}_enabled")
    if not has_value:
        return None
    return container.number_input(label, value=0.0, step=0.1, format="%.2f", key=key)


def patient_options(patients: pd.DataFrame) -> dict[str, str]:
    if patients.empty:
        return {}
    return dict(zip(patients["full_name"], patients["id"]))


def doctor_options(doctors: pd.DataFrame) -> dict[str, str]:
    if doctors.empty:
        return {}
    return dict(zip(doctors["full_name"], doctors["id"]))


def calc_age(value: Any) -> int | None:
    if pd.isna(value) or not value:
        return None
    born = pd.to_datetime(value).date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def load_data() -> dict[str, pd.DataFrame]:
    return {table: fetch_table(table) for table in TABLES}


def setup_warning() -> None:
    if supabase_client() is None:
        st.warning("Supabase ainda nao configurado.")
        st.markdown("Preencha o arquivo de configuracao local:")
        st.code(".streamlit/secrets.toml", language="text")
        st.markdown("Depois execute este script no SQL Editor do Supabase:")
        st.code("database/schema.sql", language="text")


def dashboard(data: dict[str, pd.DataFrame]) -> None:
    patients = data["patients"].copy()
    conditions = data["conditions"]
    medications = data["medications"]
    exams = data["exams"].copy()
    visits = data["visits"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pacientes", len(patients))
    col2.metric("Doencas ativas", int((conditions.get("status") == "Ativa").sum()) if not conditions.empty else 0)
    col3.metric("Medicamentos em uso", int((medications.get("status") == "Em uso").sum()) if not medications.empty else 0)
    col4.metric("Consultas", len(visits))

    left, right = st.columns(2)
    with left:
        st.subheader("Perfil etario")
        if not patients.empty and "birth_date" in patients:
            patients["idade"] = patients["birth_date"].apply(calc_age)
            patients["faixa"] = pd.cut(
                patients["idade"],
                bins=[0, 12, 18, 35, 50, 65, 120],
                labels=["0-12", "13-18", "19-35", "36-50", "51-65", "66+"],
            )
            chart_data = patients.dropna(subset=["faixa"]).groupby("faixa", observed=False).size().reset_index(name="total")
            st.plotly_chart(px.bar(chart_data, x="faixa", y="total"), use_container_width=True)
        else:
            st.info("Cadastre pacientes com data de nascimento para ver o grafico.")

    with right:
        st.subheader("Condicoes mais frequentes")
        if not conditions.empty:
            chart_data = conditions["name"].value_counts().head(10).reset_index()
            chart_data.columns = ["condicao", "total"]
            st.plotly_chart(px.bar(chart_data, x="total", y="condicao", orientation="h"), use_container_width=True)
        else:
            st.info("Cadastre condicoes clinicas para ver tendencias.")

    st.subheader("Linha do tempo de exames")
    if not exams.empty:
        exams["exam_date"] = pd.to_datetime(exams["exam_date"])
        timeline = exams.groupby([pd.Grouper(key="exam_date", freq="ME"), "exam_type"]).size().reset_index(name="total")
        st.plotly_chart(px.line(timeline, x="exam_date", y="total", color="exam_type", markers=True), use_container_width=True)
    else:
        st.info("Cadastre exames para acompanhar volume e recorrencia.")


def patient_form() -> None:
    with st.form("patient_form", clear_on_submit=True):
        st.subheader("Novo paciente")
        c1, c2, c3 = st.columns(3)
        full_name = c1.text_input("Nome completo")
        birth_date = optional_date_input("Data de nascimento", "patient_birth_date", c2)
        sex = c3.selectbox("Sexo", ["Nao informado", "Feminino", "Masculino", "Outro"])
        c4, c5, c6 = st.columns(3)
        phone = c4.text_input("Telefone")
        email = c5.text_input("Email")
        city = c6.text_input("Cidade")
        notes = st.text_area("Observacoes")
        if st.form_submit_button("Salvar paciente", type="primary"):
            if not full_name.strip():
                st.error("Informe o nome do paciente.")
            else:
                insert_row(
                    "patients",
                    {
                        "full_name": full_name,
                        "birth_date": birth_date,
                        "sex": sex,
                        "phone": phone,
                        "email": email,
                        "city": city,
                        "notes": notes,
                    },
                )


def doctor_form() -> None:
    with st.form("doctor_form", clear_on_submit=True):
        st.subheader("Novo medico")
        c1, c2, c3 = st.columns(3)
        full_name = c1.text_input("Nome")
        specialty = c2.text_input("Especialidade")
        crm = c3.text_input("CRM")
        c4, c5 = st.columns(2)
        phone = c4.text_input("Telefone")
        email = c5.text_input("Email")
        if st.form_submit_button("Salvar medico", type="primary"):
            if not full_name.strip():
                st.error("Informe o nome do medico.")
            else:
                insert_row(
                    "doctors",
                    {
                        "full_name": full_name,
                        "specialty": specialty,
                        "crm": crm,
                        "phone": phone,
                        "email": email,
                    },
                )


def clinical_forms(data: dict[str, pd.DataFrame]) -> None:
    patients = patient_options(data["patients"])
    doctors = doctor_options(data["doctors"])
    if not patients:
        st.info("Cadastre um paciente antes de adicionar historico clinico.")
        return

    tabs = st.tabs(["Doencas", "Medicamentos", "Exames", "Consultas"])

    with tabs[0], st.form("condition_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients))]
        name = st.text_input("Doenca ou condicao")
        c1, c2 = st.columns(2)
        status = c1.selectbox("Status", ["Ativa", "Controlada", "Resolvida", "Suspeita"])
        severity = c2.selectbox("Gravidade", ["Baixa", "Moderada", "Alta", "Critica"], index=1)
        diagnosed_at = optional_date_input("Data de diagnostico", "condition_diagnosed_at")
        notes = st.text_area("Observacoes")
        if st.form_submit_button("Salvar condicao", type="primary"):
            if not name.strip():
                st.error("Informe a doenca ou condicao.")
            else:
                insert_row(
                    "conditions",
                    {
                        "patient_id": patient_id,
                        "name": name,
                        "status": status,
                        "severity": severity,
                        "diagnosed_at": diagnosed_at,
                        "notes": notes,
                    },
                )

    with tabs[1], st.form("medication_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients), key="med_patient")]
        name = st.text_input("Medicamento")
        c1, c2, c3 = st.columns(3)
        dosage = c1.text_input("Dose")
        frequency = c2.text_input("Frequencia")
        status = c3.selectbox("Status", ["Em uso", "Pausado", "Encerrado"])
        c4, c5 = st.columns(2)
        started_at = optional_date_input("Inicio", "medication_started_at", c4)
        ended_at = optional_date_input("Fim", "medication_ended_at", c5)
        notes = st.text_area("Observacoes")
        if st.form_submit_button("Salvar medicamento", type="primary"):
            if not name.strip():
                st.error("Informe o medicamento.")
            else:
                insert_row(
                    "medications",
                    {
                        "patient_id": patient_id,
                        "name": name,
                        "dosage": dosage,
                        "frequency": frequency,
                        "started_at": started_at,
                        "ended_at": ended_at,
                        "status": status,
                        "notes": notes,
                    },
                )

    with tabs[2], st.form("exam_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients), key="exam_patient")]
        exam_type = st.text_input("Tipo de exame")
        c1, c2, c3 = st.columns(3)
        exam_date = c1.date_input("Data do exame", value=date.today())
        numeric_value = optional_number_input("Valor numerico", "exam_numeric_value", c2)
        unit = c3.text_input("Unidade")
        reference_range = st.text_input("Valor de referencia")
        result_text = st.text_area("Resultado descritivo")
        file_url = st.text_input("Link do arquivo")
        if st.form_submit_button("Salvar exame", type="primary"):
            if not exam_type.strip():
                st.error("Informe o tipo de exame.")
            else:
                insert_row(
                    "exams",
                    {
                        "patient_id": patient_id,
                        "exam_type": exam_type,
                        "exam_date": exam_date,
                        "result_text": result_text,
                        "numeric_value": numeric_value,
                        "unit": unit,
                        "reference_range": reference_range,
                        "file_url": file_url,
                    },
                )

    with tabs[3], st.form("visit_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients), key="visit_patient")]
        doctor_name = st.selectbox("Medico", [""] + list(doctors), key="visit_doctor")
        doctor_id = doctors.get(doctor_name)
        visit_date = st.date_input("Data da consulta", value=date.today())
        reason = st.text_area("Motivo")
        diagnosis = st.text_area("Diagnostico/hipotese")
        plan = st.text_area("Conduta/plano")
        if st.form_submit_button("Salvar consulta", type="primary"):
            insert_row(
                "visits",
                {
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "visit_date": visit_date,
                    "reason": reason,
                    "diagnosis": diagnosis,
                    "plan": plan,
                },
            )


def history_view(data: dict[str, pd.DataFrame]) -> None:
    patients = patient_options(data["patients"])
    if not patients:
        st.info("Cadastre pacientes para visualizar historicos.")
        return
    name = st.selectbox("Paciente", list(patients))
    patient_id = patients[name]
    st.subheader(name)
    for table, title in [
        ("conditions", "Doencas"),
        ("medications", "Medicamentos"),
        ("exams", "Exames"),
        ("visits", "Consultas"),
    ]:
        frame = data[table]
        st.markdown(f"**{title}**")
        if frame.empty:
            st.caption("Sem registros.")
        else:
            st.dataframe(frame[frame["patient_id"] == patient_id], use_container_width=True, hide_index=True)


def local_insights(patient_name: str, frames: dict[str, pd.DataFrame]) -> str:
    active = frames["conditions"].query("status == 'Ativa'") if not frames["conditions"].empty else pd.DataFrame()
    meds = frames["medications"].query("status == 'Em uso'") if not frames["medications"].empty else pd.DataFrame()
    exams = frames["exams"]
    parts = [
        f"Paciente: {patient_name}.",
        f"Condicoes ativas: {len(active)}.",
        f"Medicamentos em uso: {len(meds)}.",
        f"Exames registrados: {len(exams)}.",
    ]
    if not exams.empty and "numeric_value" in exams:
        numeric = exams.dropna(subset=["numeric_value"])
        if not numeric.empty:
            latest = numeric.sort_values("exam_date").tail(3)[["exam_type", "exam_date", "numeric_value", "unit"]]
            parts.append("Ultimos exames numericos: " + latest.to_dict("records").__repr__())
    if len(active) >= 3 or len(meds) >= 5:
        parts.append("Ponto de atencao: revisar polifarmacia, interacoes e prioridades do plano terapeutico.")
    return "\n".join(parts)


def ai_view(data: dict[str, pd.DataFrame]) -> None:
    patients = patient_options(data["patients"])
    if not patients:
        st.info("Cadastre pacientes para usar a analise.")
        return
    patient_name = st.selectbox("Paciente para analise", list(patients))
    patient_id = patients[patient_name]
    scoped = {
        table: frame[frame["patient_id"] == patient_id].copy() if "patient_id" in frame.columns else frame
        for table, frame in data.items()
    }
    baseline = local_insights(patient_name, scoped)
    st.text_area("Resumo estruturado", baseline, height=180)

    if st.button("Gerar analise com IA", type="primary"):
        api_key = secret("openai.api_key")
        if not api_key:
            st.info("Preencha `openai.api_key` nos secrets para habilitar IA generativa. A analise por regras ja esta acima.")
            return
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = (
                "Voce apoia organizacao de registro clinico. Nao de diagnostico definitivo. "
                "Resuma historico, tendencias, lacunas de dados e perguntas para a proxima consulta.\n\n"
                f"{baseline}\n\nDados:\n"
                f"Doencas: {scoped['conditions'].to_dict('records')}\n"
                f"Medicamentos: {scoped['medications'].to_dict('records')}\n"
                f"Exames: {scoped['exams'].to_dict('records')}\n"
                f"Consultas: {scoped['visits'].to_dict('records')}"
            )
            response = client.responses.create(
                model=secret("openai.model", "gpt-4.1-mini"),
                input=prompt,
                max_output_tokens=700,
            )
            st.markdown(response.output_text)
        except Exception as exc:
            st.error(f"Nao foi possivel gerar a analise: {exc}")


def raw_tables(data: dict[str, pd.DataFrame]) -> None:
    table = st.selectbox("Tabela", TABLES)
    st.dataframe(data[table], use_container_width=True, hide_index=True)


def main() -> None:
    st.title("Registro Clinico")
    setup_warning()
    data = load_data()

    page = st.sidebar.radio(
        "Navegacao",
        ["Dashboard", "Pacientes", "Medicos", "Historico clinico", "Historico por paciente", "IA", "Tabelas"],
    )

    if page == "Dashboard":
        dashboard(data)
    elif page == "Pacientes":
        patient_form()
        st.dataframe(data["patients"], use_container_width=True, hide_index=True)
    elif page == "Medicos":
        doctor_form()
        st.dataframe(data["doctors"], use_container_width=True, hide_index=True)
    elif page == "Historico clinico":
        clinical_forms(data)
    elif page == "Historico por paciente":
        history_view(data)
    elif page == "IA":
        ai_view(data)
    else:
        raw_tables(data)


if __name__ == "__main__":
    main()
