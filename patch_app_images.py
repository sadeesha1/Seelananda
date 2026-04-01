import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the Full Run phase 2 call
text = text.replace(
    'st.session_state.image_results = generate_all_images(prompts, folder, active_lora)',
    'st.session_state.image_results = generate_all_images(prompts, folder, active_lora, IMAGE_MODELS[image_model_choice])'
)

# Replace the singular phase 2 Gen Images button call
text = text.replace(
    'image_results = generate_all_images(\n                            st.session_state.image_prompts,\n                            Path(st.session_state.run_folder),\n                            st.session_state.get("lora_url", "").strip(),\n                            progress_cb=progress_cb\n                        )',
    'image_results = generate_all_images(\n                            st.session_state.image_prompts,\n                            Path(st.session_state.run_folder),\n                            st.session_state.get("lora_url", "").strip(),\n                            IMAGE_MODELS[image_model_choice],\n                            progress_cb=progress_cb\n                        )'
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
