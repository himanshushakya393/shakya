import streamlit as st
import pandas as pd
import plotly.express as px
import io
from fpdf import FPDF
import os
import tempfile
import plotly.io as pio
pio.renderers.default = "png"

try:
    import kaleido
except ImportError:
    import streamlit as st
    st.error("Kaleido is not installed in the environment.")

st.set_page_config(page_title="DYNAMIC CHART", layout="wide")
st.title("📊 Dynamic Chart Builder")
st.markdown("**Developed by Himanshu Shakya**, [LinkedIn](https://www.linkedin.com/in/himanshu-shakya-9172b7358/)")

uploaded_file = st.file_uploader("📤 Upload Excel or CSV file", type=["xlsx", "xls", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(("xlsx", "xls")):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    st.success("✅ File loaded successfully!")

    st.sidebar.header("🔍 Filter Data")
    for col in ['OUT OF SERVICE CATEGORY', 'arrival_date_year']:
        if col in df.columns:
            options = df[col].dropna().unique().tolist()
            selected = st.sidebar.multiselect(f"Filter by {col}", sorted(options))
            if selected:
                df = df[df[col].isin(selected)]

    shape = df.shape
    st.success("Your data has {} rows and {} columns.".format(shape[0], shape[1]))

    st.markdown("## 📈 Build Your Charts")

    chart_count = st.number_input("How many charts would you like to create?", min_value=1, max_value=10, step=1, value=1)

    conclusions = []
    fig_images = []

    def save_chart_as_image(fig):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                fig.write_image(tmpfile.name)
                with open(tmpfile.name, "rb") as f:
                    img_bytes = f.read()
            os.remove(tmpfile.name)
            return img_bytes
        except Exception as e:
            st.warning(f"Error saving chart image: {e}")
            return None

    for i in range(chart_count):
        st.markdown(f"### Chart {i+1}")
        chart_type = st.selectbox(f"Chart Type {i+1}", ["Bar Chart", "Line Chart", "Pie Chart"], key=f"type_{i}")
        group_col = st.selectbox(f"X-axis (grouping) {i+1}", df.columns, key=f"group_{i}")
        value_col = st.selectbox(f"Y-axis (value or count) {i+1}", df.columns, key=f"value_{i}")

        # Logic for counting if X == Y
        if group_col == value_col:
            plot_df = df[group_col].value_counts().reset_index()
            plot_df.columns = [group_col, 'count']
            value_col = 'count'
            agg_type = 'count'
        else:
            if pd.api.types.is_numeric_dtype(df[value_col]):
                plot_df = df.groupby(group_col)[value_col].sum().reset_index()
                agg_type = 'sum'
            else:
                plot_df = df.groupby(group_col)[value_col].count().reset_index()
                plot_df.rename(columns={value_col: 'count'}, inplace=True)
                value_col = 'count'
                agg_type = 'count'

        # Plotting the chart
        if chart_type == "Bar Chart":
            fig = px.bar(plot_df, x=group_col, y=value_col, text_auto=True,
                         title=f"{agg_type.capitalize()} of {value_col} by {group_col}")
        elif chart_type == "Line Chart":
            fig = px.line(plot_df, x=group_col, y=value_col, markers=True,
                          title=f"{agg_type.capitalize()} of {value_col} by {group_col}")
        else:
            fig = px.pie(plot_df, names=group_col, values=value_col,
                         title=f"{agg_type.capitalize()} of {value_col} by {group_col}")

        fig.update_layout(template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

        # Conclusion
        max_group = plot_df.loc[plot_df[value_col].idxmax(), group_col]
        max_value = plot_df[value_col].max()
        percent = round((max_value / plot_df[value_col].sum()) * 100, 2)
        if chart_type != "Line Chart":
            msg = f"'{max_group}' has the highest {value_col} with {percent}% of the total."
        else:
            msg = f"'{max_group}' shows the peak {value_col} with {percent}% share."
        conclusions.append(msg)
        st.success(msg)

        img_bytes = save_chart_as_image(fig)
        if img_bytes:
            fig_images.append(img_bytes)

    if conclusions:
        st.markdown("## 📌 Overall Summary")
        for i, text in enumerate(conclusions):
            st.markdown(f"**Chart {i+1}:** {text}")

    st.markdown("## 💾 Download Final Data")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    buffer.seek(0)
    st.download_button("📥 Download Dataset as Excel", data=buffer, file_name="hotel_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def generate_pdf_charts(images):
        pdf = FPDF()
        for i, img in enumerate(images):
            temp_img = os.path.join(tempfile.gettempdir(), f"chart_{i}.png")
            with open(temp_img, "wb") as f:
                f.write(img)
            pdf.add_page()
            pdf.image(temp_img, x=10, w=190)
            os.remove(temp_img)
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        output = io.BytesIO(pdf_bytes)
        output.seek(0)
        return output

    def generate_pdf_conclusions(concs):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "Overall Summary:", ln=True)
        for i, text in enumerate(concs):
            clean_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, f"Chart {i+1}: {clean_text}")
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        output = io.BytesIO(pdf_bytes)
        output.seek(0)
        return output

    def generate_full_report(images, concs):
        pdf = FPDF()
        for i, img in enumerate(images):
            temp_img = os.path.join(tempfile.gettempdir(), f"chart_full_{i}.png")
            with open(temp_img, "wb") as f:
                f.write(img)
            pdf.add_page()
            pdf.image(temp_img, x=10, w=190)
            os.remove(temp_img)
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "Overall Summary:", ln=True)
        for i, text in enumerate(concs):
            clean_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, f"Chart {i+1}: {clean_text}")
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        output = io.BytesIO(pdf_bytes)
        output.seek(0)
        return output

    if fig_images:
        st.markdown("## 📤 Download PDF Reports")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("📄 Download Only Charts", data=generate_pdf_charts(fig_images), file_name="charts_only.pdf", mime="application/pdf")
        with col2:
            st.download_button("📝 Download Only Conclusions", data=generate_pdf_conclusions(conclusions), file_name="conclusions_only.pdf", mime="application/pdf")
        with col3:
            st.download_button("📘 Download Full Report", data=generate_full_report(fig_images, conclusions), file_name="full_report.pdf", mime="application/pdf")
    else:
        st.warning("⚠️ No charts generated yet.")

st.markdown("<hr style='margin-top: 50px;'>", unsafe_allow_html=True)

footer_html = """
    <div style="text-align: center; color: gray; font-size: 14px; padding-top: 10px;">
        © 2025 | Developed by <strong>Himanshu Shakya</strong>
    </div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
