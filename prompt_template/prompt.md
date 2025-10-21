### **GIẢI THÍCH CÁC THAM SỐ NÂNG CAO:**

*   **`negative_prompt`**: Yêu cầu AI *tránh* tạo ra những yếu tố không mong muốn (ví dụ: hình ảnh mờ, nhân vật biến dạng, các chi tiết sai thời đại).
*   **`lighting`**: Mô tả cụ thể loại ánh sáng và hiệu ứng của nó để tạo ra không khí cho cảnh quay (ví dụ: ánh sáng vàng ấm của bình minh, ánh sáng tương phản gắt gao).
*   **`color_palette`**: Chỉ định tông màu chủ đạo của cảnh (ví dụ: tông màu hoài cổ sepia, màu rực rỡ của lễ hội, màu xanh lạnh của công nghệ).
*   **`composition`**: Hướng dẫn AI về cách sắp xếp các yếu tố trong khung hình theo các quy tắc điện ảnh (ví dụ: quy tắc 1/3, góc máy thấp, cận cảnh).
*   **`details`**: Thêm vào các chi tiết nhỏ nhưng quan trọng để tăng tính chân thực (ví dụ: hiệu ứng hạt phim, tia sáng lóe qua ống kính).

---

### **KỊCH BẢN VÀ PROMPT JSON CHI TIẾT**

#### **PHÂN CẢNH 1 (0-8s): KHÚC KHẢI HOÀN CỦA HIỆN TẠI**

*   **Lời dẫn của MC:** "Kính thưa quý vị khán giả! 80 năm! Một hành trình dài với những dấu son không thể phai mờ. Chào mừng đến với chương trình đặc biệt, nhìn lại 80 năm ngày Quốc khánh nước Cộng hòa Xã hội Chủ nghĩa Việt Nam!"

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "An epic, hyper-realistic 8K aerial drone shot, soaring upwards over a futuristic Ho Chi Minh City at night. The sky explodes with magnificent, multi-colored fireworks celebrating Vietnam's 80th National Day. The Landmark 81 skyscraper is a beacon, its entire facade a giant, glowing projection of the Vietnamese flag. Below, streets are rivers of light from traffic trails. The atmosphere is overwhelmingly celebratory and patriotic.",
      "negative_prompt": "blurry, low-resolution, generic buildings, cartoonish fireworks, dark unlit areas, empty streets",
      "style": "cinematic, hyper-realistic, high dynamic range (HDR)",
      "duration": 8,
      "camera_movement": "smooth crane shot moving upwards and slightly rotating",
      "lighting": "vibrant neon glow from city lights, bright explosive light from fireworks, deep night sky contrast",
      "color_palette": "deep blues, blacks, vibrant reds and yellows from the flag and fireworks, electric white",
      "composition": "wide establishing shot, Landmark 81 centered as the focal point",
      "details": "crisp reflections on glass buildings, visible trails of individual fireworks, sense of immense scale"
    }
    ```

---

#### **PHÂN CẢNH 2 (8-16s): ĐÊM DÀI NÔ LỆ**

*   **Lời dẫn của MC:** "Nhưng để có được ánh sáng hôm nay, dân tộc ta đã phải đi qua những đêm dài nô lệ, dưới gót giày của thực dân, lầm than và tủi cực."

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "A powerful, emotional historical recreation. An extreme close-up on the weathered, determined face of an elderly Vietnamese farmer under French colonial rule. His eyes hold a universe of resilience and unspoken strength. The background is a shallow depth of field, showing blurred silhouettes of people toiling in a sun-scorched rice paddy.",
      "negative_prompt": "smiling, well-fed, clean clothes, modern elements, cartoonish features, neutral expression",
      "style": "vintage 1930s black and white film, high contrast, grainy texture",
      "duration": 8,
      "camera_movement": "very slow, subtle zoom-in on the farmer's eyes",
      "lighting": "harsh, dramatic top-down sunlight creating deep shadows, chiaroscuro effect on the face",
      "color_palette": "monochromatic, deep blacks, stark whites, muted greys, sepia tint",
      "composition": "tight close-up, rule of thirds, focus entirely on the eyes",
      "details": "visible film grain, dust and scratches effect, sweat on the brow, texture of wrinkled skin"
    }
    ```

---

#### **PHÂN CẢNH 3 (16-24s): MÙA THU CÁCH MẠNG**

*   **Lời dẫn của MC:** "Và rồi, Mùa thu tháng Tám năm 1945 đã đến! Cả dân tộc triệu người như một, nhất tề vùng lên, phá tan xiềng xích!"

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "A dynamic, epic recreation of the August Revolution. A low-angle shot from within a massive, roaring crowd marching towards the Hanoi Opera House. Thousands of determined faces are visible, shouting slogans. The air is thick with energy as countless red flags with yellow stars wave like a sea of fire. The scene transitions from black and white to color midway through.",
      "negative_prompt": "static, passive crowd, empty spaces, modern clothing, few flags",
      "style": "colorized historical footage, epic scale, gritty realism",
      "duration": 8,
      "camera_movement": "handheld, sweeping pan that moves with the crowd to convey energy",
      "lighting": "bright, slightly overexposed daylight suggesting a historic, bright new day",
      "color_palette": "dominant revolutionary red and yellow, with muted, desaturated background colors to make the flags pop",
      "composition": "low-angle to empower the crowd, leading lines created by the marching people",
      "details": "motion blur, authentic period clothing, passionate facial expressions"
    }
    ```
*(Và tiếp tục cho các phân cảnh còn lại...)*

---

#### **PHÂN CẢNH 4 (24-32s): GIỌNG NÓI LỊCH SỬ**

*   **Lời dẫn của MC:** "Ngày 2 tháng 9... Tại quảng trường Ba Đình lịch sử... Chủ tịch Hồ Chí Minh đã đọc bản Tuyên ngôn Độc lập, khai sinh ra nước Việt Nam Dân chủ Cộng hòa!"

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "A photorealistic, respectful recreation of President Ho Chi Minh on the podium at Ba Dinh Square. The camera is positioned behind his shoulder, showing the historic document in his hands, looking out at an endless sea of people listening intently. A gentle breeze rustles the flag behind him.",
      "negative_prompt": "distracting elements, modern technology, casual crowd, incorrect attire, empty podium",
      "style": "photorealistic, cinematic, solemn",
      "duration": 8,
      "camera_movement": "slow, respectful push-in towards the crowd over Ho Chi Minh's shoulder",
      "lighting": "bright, clear autumn sunlight, creating a slight halo effect, long shadows symbolizing the end of an era",
      "color_palette": "natural, warm tones, the red of the flag is vibrant but not overwhelming",
      "composition": "over-the-shoulder shot, creating a sense of being there, immense scale",
      "details": "texture of the aged paper, meticulous detail on clothing, individual faces visible in the crowd"
    }
    ```

---

#### **PHÂN CẢNH 5 (32-40s): LỬA THỬ VÀNG**

*   **Lời dẫn của MC:** "Nền độc lập non trẻ đã phải đi qua những cuộc chiến tranh vệ quốc vĩ đại, được tôi luyện trong gian lao và trả giá bằng xương máu."

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "An artistic, symbolic montage about resilience during war. A silhouette of a young soldier against a blood-red sunset. A young female volunteer's determined eyes seen through thick jungle leaves. A mother's hand tightly gripping her son's before he leaves. The focus is on emotion and sacrifice, not combat.",
      "negative_prompt": "graphic violence, gore, explicit combat, guns firing, explosions",
      "style": "painterly, cinematic, symbolic, high-contrast silhouettes",
      "duration": 8,
      "effect": "artistic cross-dissolves between three distinct, powerful images",
      "lighting": "dramatic, low-key lighting, rim lighting on silhouettes, god rays through jungle canopy",
      "color_palette": "deep reds, dark greens, earthy browns, heavily desaturated tones",
      "composition": "strong silhouettes, emotional close-ups on hands and eyes",
      "details": "rain drops, mist in the jungle, texture of coarse fabric"
    }
    ```
---

#### **PHÂN CẢNH 6 (40-48s): VƯƠN MÌNH TỪ ĐỐNG TRO TÀN**

*   **Lời dẫn của MC:** "Hòa bình lập lại, từ trong hoang tàn đổ nát, Việt Nam đã vươn mình đứng dậy, viết nên câu chuyện thần kỳ về tái thiết và đổi mới."

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "A spectacular time-lapse hyper-morph sequence showing Vietnam's economic miracle. The scene begins on a post-war desolate field, which seamlessly transforms into a lush, green rice paddy. Scaffolding grows like vines, forming a modern factory. The factory then morphs into the stunning Dragon Bridge in Da Nang at night, breathing a plume of fire.",
      "negative_prompt": "abrupt cuts, disjointed transitions, unrealistic architecture, static image",
      "style": "hyperlapse, morphing CGI, dynamic and seamless",
      "duration": 8,
      "camera_movement": "static camera, witnessing the transformation unfold in fast-forward",
      "lighting": "transitions from bleak grey light to warm sunrise to vibrant city night lights",
      "color_palette": "shifts from grey/browns to vibrant greens, then to industrial metallics, ending with neon blues and fiery oranges",
      "composition": "centered subject, constant horizon line for a smooth transition",
      "details": "sparks from construction, steam from factories, realistic fire and water from the dragon bridge"
    }
    ```
---

#### **PHÂN CẢNH 7 (48-56s): BẢN SẮC NGÀN NĂM**

*   **Lời dẫn của MC:** "Phát triển nhưng không hòa tan. Việt Nam vẫn luôn giữ trọn vẹn bản sắc văn hóa ngàn năm văn hiến."

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "A vibrant, quick-cut montage celebrating Vietnamese culture. A graceful woman in a flowing white Ao Dai walking through the Temple of Literature. An extreme close-up of an artisan's hands meticulously applying paint to Bat Trang ceramics. The shimmering, magical lanterns of Hoi An at night reflected in the river. A dynamic shot of a water puppet show performance.",
      "negative_prompt": "dull colors, modern objects, touristy look, empty scenes, generic",
      "style": "cinematic, vibrant color grading, beautiful and elegant",
      "duration": 8,
      "effect": "fast, rhythmic cuts perfectly timed to music",
      "lighting": "warm, soft, inviting light for Ao Dai and ceramics; magical, glowing light for lanterns",
      "color_palette": "a rich tapestry of traditional colors: imperial reds, golds, deep greens, jade, warm lantern yellows",
      "composition": "elegant close-ups, symmetrical shots, beautiful shallow depth of field",
      "details": "texture of silk, reflections in water, intricate patterns on ceramics"
    }
    ```
---

#### **PHÂN CẢNH 8 (56-64s): DẤU ẤN TRÊN TRƯỜNG QUỐC TẾ**

*   **Lời dẫn của MC:** "Và hôm nay, Việt Nam là một quốc gia có trách nhiệm, một người bạn tin cậy, tự tin khẳng định vị thế của mình trên trường quốc tế."

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "A sleek, high-tech montage of modern Vietnam's global presence. A VinFast electric car with futuristic headlights gliding on a wet, neon-lit international street. A Vietnamese scientist in a sterile, state-of-the-art laboratory examining a glowing holographic display. The Vinasat satellite majestically orbiting the Earth, with the sun glinting off its solar panels.",
      "negative_prompt": "cluttered, old technology, messy lab, blurry images, generic car",
      "style": "high-tech, futuristic, clean aesthetic, polished",
      "duration": 8,
      "camera_movement": "dynamic, smooth motion graphics combined with slick live-action shots",
      "lighting": "clean, high-key studio lighting for the lab; anamorphic lens flares for the car; hard sunlight in space",
      "color_palette": "cool color palette of blues, silvers, and whites with sharp, glowing accents",
      "composition": "dynamic angles, focus on clean lines and modern design",
      "details": "polished metallic surfaces, glowing data streams, lens flares, detailed reflection of Earth on the satellite"
    }
    ```
---

#### **PHÂN CẢNH 9 (64-72s): NGỌN LỬA TRAO TAY**

*   **Lời dẫn của MC:** "80 năm, ngọn lửa của khát vọng độc lập, tự do và hùng cường đã được trao lại cho thế hệ trẻ - những người sẽ viết tiếp trang sử vàng của dân tộc."

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "A heartwarming, optimistic slow-motion shot. An adorable little girl with a small Vietnamese flag painted on her cheek laughs directly at the camera. A diverse group of university students in a bright, modern co-working space energetically brainstorm around a table. A young female athlete raises a trophy, pure joy on her face.",
      "negative_prompt": "sad expressions, dark lighting, bleak environment, blurry faces, old-fashioned setting",
      "style": "optimistic, heartwarming, commercial-grade slow-motion (120fps)",
      "duration": 8,
      "camera_movement": "gentle orbiting shot around the subjects, creating a feeling of inclusion",
      "lighting": "warm, soft, backlit 'golden hour' glow, creating a hopeful and dreamlike atmosphere",
      "color_palette": "bright, warm, optimistic colors; pastels, whites, and natural skin tones",
      "composition": "intimate medium shots and close-ups, shallow depth of field to focus on their hopeful expressions",
      "details": "genuine smiles, catchlights in their eyes, dust motes floating in the golden light"
    }
    ```
---

#### **PHÂN CẢNH 10 (72-80s): TƯƠNG LAI RẠNG RỠ**

*   **Lời dẫn của MC:** "Việt Nam! Hành trình 80 năm rực rỡ và một tương lai còn vĩ đại hơn nữa đang chờ! Xin kính chào và hẹn gặp lại!"

*   **Prompt JSON cho AI (Chi tiết):**
    ```json
    {
      "prompt": "The ultimate epic final shot. An immense, photorealistic Vietnamese flag waves majestically in cinematic slow motion, filling the entire frame against a brilliant blue sky. The camera slowly pulls back, and as it does, the flag's fabric seamlessly dissolves into a glowing, golden, 3D map of Vietnam as seen from the high orbit of space. The S-shaped country shines brightly against the darkness. The text 'VIỆT NAM: 80 NĂM RỰC RỠ' appears elegantly.",
      "negative_prompt": "small flag, cloudy sky, wrinkled flag, unrealistic Earth, blurry map, generic font",
      "style": "epic, majestic, symbolic, high-end visual effects",
      "duration": 8,
      "camera_movement": "slow, dramatic pull-back (dolly zoom effect) combined with a dissolve transition",
      "lighting": "brilliant, epic sunlight creating beautiful ripples and texture on the flag's fabric, ethereal glow from the map",
      "color_palette": "vibrant red, gold, and deep blue of the sky and space",
      "composition": "starts as a full frame of the flag, ends with the S-shaped map perfectly centered",
      "details": "realistic cloth physics, atmospheric haze on Earth's curve, subtle starlight"
    }
    ```