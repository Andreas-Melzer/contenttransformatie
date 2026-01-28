import streamlit as st
import json
import bcrypt
import time
from datetime import datetime, timedelta  # Voeg deze import toe
import extra_streamlit_components as cookie_manager
from pathlib import Path
from contentcreatie.config.paths import paths

def get_manager():
    return cookie_manager.CookieManager(key="auth_cookie_manager")

def require_access():
    cookie_mgr = get_manager()
    
    if st.session_state.get("cached_user_email"):
        return st.session_state.cached_user_email

    # Cookies ophalen
    saved_user = cookie_mgr.get(cookie="auth_user_email")
    if saved_user:
        st.session_state.cached_user_email = saved_user
        return saved_user

    st.title("Inloggen")
    
    with st.form("login_form"):
        email_input = st.text_input("E-mailadres", autocomplete="username").lower().strip()
        password_input = st.text_input("Wachtwoord", type="password", autocomplete="current-password")
        submit = st.form_submit_button("Inloggen")

        if submit:
            user_data_path = Path(paths.user_data)
            
            if user_data_path.exists():
                with open(user_data_path, 'r') as f:
                    user_db = json.load(f)
                
                stored_hash = user_db.get(email_input)

                if stored_hash and bcrypt.checkpw(password_input.encode('utf-8'), stored_hash.encode('utf-8')):
                    st.session_state.cached_user_email = email_input
                    
                    expiry_date = datetime.now() + timedelta(days=30)
                    
                    cookie_mgr.set(
                        "auth_user_email", 
                        email_input, 
                        expires_at=expiry_date 
                    )
                    
                    st.success("Succesvol ingelogd!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Onjuist e-mailadres of wachtwoord.")
            else:
                st.error("Systeemfout: Gebruikerslijst niet gevonden.")
    
    st.stop()