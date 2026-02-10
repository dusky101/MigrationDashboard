"""
Custom CSS Styling

Professional styling for the Migration Dashboard.
Provides a clean, modern look with proper visual hierarchy.
"""


def get_custom_css() -> str:
    """
    Returns custom CSS for the Streamlit application.
    
    Features:
    - Professional color scheme
    - Improved spacing and typography
    - Enhanced metric cards
    - Better status badges
    - Cleaner tables
    - Responsive layout improvements
    
    Returns:
        CSS string to be injected via st.markdown()
    """
    return """
    <style>
      /* ===================================================================
         GLOBAL LAYOUT & SPACING
         =================================================================== */
      
      /* Main content area - use full viewport width */
      section.main > div.block-container {
        max-width: 100% !important;
        padding-left: 2.0rem !important;
        padding-right: 2.0rem !important;
        padding-top: 1rem !important;
      }

      /* Compact sidebar */
      [data-testid="stSidebar"] {
        min-width: 320px !important;
        max-width: 320px !important;
      }

      /* Collapsed sidebar takes no space */
      [data-testid="stSidebar"][aria-expanded="false"] {
        min-width: 0px !important;
        max-width: 0px !important;
        width: 0px !important;
      }

      /* Sidebar collapse control positioning */
      [data-testid="collapsedControl"] {
        position: fixed !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
        z-index: 9999 !important;
      }

      /* Wider layouts get more breathing room */
      @media (min-width: 1400px) {
        section.main > div.block-container {
          padding-left: 2.5rem !important;
          padding-right: 2.5rem !important;
        }
      }

      /* ===================================================================
         TYPOGRAPHY
         =================================================================== */
      
      /* Cleaner headers */
      h1, h2, h3 {
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
      }

      /* Better paragraph spacing */
      p {
        line-height: 1.6 !important;
      }

      /* ===================================================================
         METRIC CARDS
         =================================================================== */
      
      /* Enhanced metric cards */
      [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        padding: 1rem 1.25rem !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
      }

      [data-testid="stMetric"] label {
        color: rgba(255, 255, 255, 0.9) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
      }

      [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
      }

      [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: rgba(255, 255, 255, 0.85) !important;
      }

      /* ===================================================================
         BUTTONS & INTERACTIONS
         =================================================================== */
      
      /* Primary buttons */
      .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4) !important;
        transition: all 0.3s ease !important;
      }

      .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.6) !important;
        transform: translateY(-2px) !important;
      }

      /* Regular buttons */
      .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
      }

      .stButton > button:hover {
        border-color: #667eea !important;
        color: #667eea !important;
      }

      /* Download buttons */
      .stDownloadButton > button {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 6px rgba(17, 153, 142, 0.4) !important;
      }

      .stDownloadButton > button:hover {
        box-shadow: 0 6px 12px rgba(17, 153, 142, 0.6) !important;
        transform: translateY(-2px) !important;
      }

      /* ===================================================================
         STATUS BADGES
         =================================================================== */
      
      /* Success/Complete status */
      .element-container:has(> .stSuccess) {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(17, 153, 142, 0.3) !important;
      }

      /* Warning/In Progress status */
      .element-container:has(> .stWarning) {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(245, 87, 108, 0.3) !important;
      }

      /* Info status */
      .element-container:has(> .stInfo) {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%) !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(79, 172, 254, 0.3) !important;
      }

      /* Error status */
      .element-container:has(> .stError) {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%) !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(250, 112, 154, 0.3) !important;
      }

      /* ===================================================================
         TABLES & DATAFRAMES
         =================================================================== */
      
      /* Cleaner dataframes */
      [data-testid="stDataFrame"] {
        border-radius: 10px !important;
        overflow: hidden !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
      }

      /* Table headers */
      [data-testid="stDataFrame"] thead tr {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
      }

      [data-testid="stDataFrame"] thead th {
        color: white !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.05em !important;
      }

      /* Alternating row colours */
      [data-testid="stDataFrame"] tbody tr:nth-child(even) {
        background-color: rgba(102, 126, 234, 0.03) !important;
      }

      /* ===================================================================
         FORM ELEMENTS
         =================================================================== */
      
      /* Improved input fields */
      .stTextInput > div > div > input,
      .stTextArea > div > div > textarea {
        border-radius: 8px !important;
        border: 2px solid #e0e0e0 !important;
        transition: border-color 0.2s ease !important;
      }

      .stTextInput > div > div > input:focus,
      .stTextArea > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
      }

      /* Select boxes */
      .stSelectbox > div > div {
        border-radius: 8px !important;
      }

      /* Multiselect */
      .stMultiSelect > div > div {
        border-radius: 8px !important;
      }

      /* ===================================================================
         TABS
         =================================================================== */
      
      /* Enhanced tabs */
      .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: rgba(102, 126, 234, 0.05) !important;
        padding: 0.5rem !important;
        border-radius: 10px !important;
      }

      .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
      }

      .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
      }

      /* ===================================================================
         EXPANDERS
         =================================================================== */
      
      /* Cleaner expanders */
      .streamlit-expanderHeader {
        background-color: rgba(102, 126, 234, 0.05) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: background-color 0.2s ease !important;
      }

      .streamlit-expanderHeader:hover {
        background-color: rgba(102, 126, 234, 0.1) !important;
      }

      /* ===================================================================
         DIVIDERS
         =================================================================== */
      
      hr {
        margin: 2rem 0 !important;
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, 
          transparent 0%, 
          rgba(102, 126, 234, 0.3) 50%, 
          transparent 100%) !important;
      }

      /* ===================================================================
         POPOVER (for groups display)
         =================================================================== */
      
      [data-testid="stPopover"] {
        border-radius: 10px !important;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15) !important;
      }

      /* ===================================================================
         ACCESSIBILITY & POLISH
         =================================================================== */
      
      /* Smooth scrolling */
      html {
        scroll-behavior: smooth !important;
      }

      /* Better focus indicators */
      *:focus-visible {
        outline: 2px solid #667eea !important;
        outline-offset: 2px !important;
      }

      /* Loading spinner */
      .stSpinner > div {
        border-top-color: #667eea !important;
      }

    </style>
    """