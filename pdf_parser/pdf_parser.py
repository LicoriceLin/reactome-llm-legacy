# adapted from https://github.com/Weixin-Liang/LLM-scientific-feedback.git
import pikepdf
import io
import requests
import xml.etree.ElementTree as ET

def extract_element_text(element):
    if element.text:
        text = element.text
    else:
        text = " "
    for child in element:
        text += " " + extract_element_text(child)
        if child.tail:
            text += " " + child.tail
    return text

def get_main_content(root):
    """
    Get the main content of the paper, excluding the figures and tables section, usually no abstract too.

    Args:
        root: root of the xml file
    Returns:
        main_content_str: string of the main content of the paper

    """

    main_content_str = ""
    # Get all section elements
    sections = root.findall(".//sec")
    for sec in sections:  # Exclude the figures section
        # Get the section title if available
        title = sec.find("title")

        # Exclude Figures section
        if title is not None and (title.text == "Figures"):
            continue
        elif title is not None:
            main_content_str += f"\nSection Title: {title.text}\n"  # Yes, title will duplicate with extract_element_text

        main_content_str += extract_element_text(sec)
        main_content_str += "\n"

    return main_content_str

def get_article_title(root):
    article_title = root.find(".//article-title")
    if article_title is not None:
        title_text = article_title.text
        return title_text
    else:
        return "Artitle Title"  # not found

def get_abstract(root):
    # find the abstract element and print its text content
    abstract = root.find(".//abstract/p")
    if abstract is not None:
        return abstract.text

    abstract = root.find(".//sec[title='Abstract']")
    if abstract is not None:
        return extract_element_text(abstract)

    return "Abstract"  # not found


def get_figure_and_table_captions(root):
    """
    Extracts all figure and table captions from the given root element and returns them as a concatenated string.
    """
    captions = []

    # Get Figures section
    figures = root.find('.//sec[title="Figures"]')
    if figures is not None:
        # Print Figures section content
        for child in figures:
            if child.tag == "fig":
                title = child.find("caption/title")
                caption = child.find("caption/p")
                if title is not None and title.text is not None:
                    title_text = title.text.strip()
                else:
                    title_text = ""
                if caption is not None and caption.text is not None:
                    caption_text = caption.text.strip()
                else:
                    caption_text = ""
                captions.append(f"{title_text} {caption_text}")

    # Print all table contents
    table_wraps = root.findall(".//table-wrap")
    if table_wraps is not None:
        for table_wrap in table_wraps:
            title = table_wrap.find("caption/title")
            caption = table_wrap.find("caption/p")
            if title is not None and title.text is not None:
                title_text = title.text.strip()
            else:
                title_text = ""
            if caption is not None and caption.text is not None:
                caption_text = caption.text.strip()
            else:
                caption_text = ""
            captions.append(f"{title_text} {caption_text}")

    return "\n".join(captions)

def get_main_content(root):
    """
    Get the main content of the paper, excluding the figures and tables section, usually no abstract too.

    Args:
        root: root of the xml file
    Returns:
        main_content_str: string of the main content of the paper

    """

    main_content_str = ""
    # Get all section elements
    sections = root.findall(".//sec")
    for sec in sections:  # Exclude the figures section
        # Get the section title if available
        title = sec.find("title")

        # Exclude Figures section
        if title is not None and (title.text == "Figures"):
            continue
        elif title is not None:
            main_content_str += f"\nSection Title: {title.text}\n"  # Yes, title will duplicate with extract_element_text

        main_content_str += extract_element_text(sec)
        main_content_str += "\n"

    return main_content_str

def get_section_text(root, section_title="Introduction"):
    """
    Warning: When introduction have subsection-like paragraph, it would be think of as another section by XML.

    Extracts the text content of a section with the given title from the given root element.

    :param root: The root element of an XML document.
    :param section_title: The title of the section to extract. Case-insensitive.
    :return: The text content of the section as a string.
    """
    section = None
    for sec in root.findall(".//sec"):
        title_elem = sec.find("title")
        if title_elem is not None and title_elem.text.lower() == section_title.lower():
            section = sec
            break
    # If no matching section is found, return an empty string
    if section is None:
        return ""

    return extract_element_text(section)

def parse_pdf(input_file: str):
    assert input_file.endswith(".pdf"), "Input file must be a PDF file."

    input_pdf = pikepdf.Pdf.open(input_file)
    output_pdf = pikepdf.Pdf.new()

    for page_num in range(
        min(10, len(input_pdf.pages))
    ):  # TODO: Currently only first 10 pages
        output_pdf.pages.append(input_pdf.pages[page_num])

    output_stream = io.BytesIO()
    output_pdf.save(output_stream)
    output_stream.seek(0)

    # Send the POST request to the conversion service
    headers = {"Content-Type": "application/pdf"}
    convert_url = "http://localhost:8080/api/convert"
    try:
        response = requests.post(
            convert_url, headers=headers, data=output_stream.getvalue()
        )
    except:
        raise RuntimeError('run this before: conda acticvate ScienceBeam; python -m sciencebeam_parser.service.server --port=8080')
    xml=response.content.decode()
    xml_file = io.StringIO(xml)
    tree = ET.parse(xml_file)
    root = tree.getroot()

    title = get_article_title(root)
    abstract = get_abstract(root)
    introduction = get_section_text(root, section_title="Introduction")
    figure_and_table_captions = get_figure_and_table_captions(root)

    # Get all section titles, including Figures
    section_titles = [
        sec.find("title").text if sec.find("title") is not None else ""
        for sec in root.findall(".//sec")
    ]

    # Get Main_content section, including Introduction, but excluding Figures
    main_content = get_main_content(root)
    
    return {
        "title": title,
        "abstract": abstract,
        "introduction": introduction,
        "figure_and_table_captions": figure_and_table_captions,
        "section_titles": section_titles,
        "main_content": main_content,
    }