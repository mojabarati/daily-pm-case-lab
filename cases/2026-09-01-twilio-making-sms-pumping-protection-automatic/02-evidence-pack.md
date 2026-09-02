# Evidence Pack

## خط زمانی

- **اوایل ۲۰۲۲:** Twilio می‌گوید پیش از اعلام public beta، با شمار محدودی از مشتریان pilot اجرا کرده است؛ اما اندازهٔ cohort، معیار انتخاب، کنترل، روش آزمایش و metricهای زیربنایی منتشر نشده‌اند. **FACT (گزارش شرکت؛ جزئیات ناکافی)** [S02]
- **۱۴ ژوئیهٔ ۲۰۲۲:** یک پست توسعه‌دهندگان Twilio اعلام کرد قابلیت در public beta است و از کنترل‌های مشتری‌مدارِ rate limit، geo permissions و CAPTCHA/bot controls نیز گفت. **FACT** [S03]
- **۲۵ ژوئیهٔ ۲۰۲۲:** changelog از beta و عملکرد خودکارِ بدون هزینهٔ اضافی خبر داد و موارد pilot با کاهش تا ۳۵٪ هزینهٔ روزانه و دوبرابرشدن conversion در بعضی کشورها را گزارش کرد. **FACT (ادعای شرکت؛ روش منتشر نشده)** [S01]
- **۶ سپتامبر ۲۰۲۲:** Twilio اعلان رسمی public beta و امکان فعال‌سازی در Console را منتشر کرد. **FACT** [S02]
- **۸ اوت ۲۰۲۳:** رئیس Twilio Communications این release را بخشی از ورود AI/ML به محصولات core دانست و گفت در یک expansion deal نقش مهمی داشته است. **FACT (اظهار مدیریت؛ ارزش deal افشا نشده)** [S05]
- **۱۰ ژوئیهٔ ۲۰۲۴:** شرایط حقوقی، سازوکار credit مشروط و استثناهای آن را مشخص کرد. **FACT** [S06]
- **۸ اوت ۲۰۲۴:** راهنمای محصول، سطوح حفاظت و بازه‌های false positive ادعاشده را منتشر کرد. **FACT (ادعای Twilio، نه audit مستقل)** [S07]
- **ژوئن ۲۰۲۲ تا اکتبر ۲۰۲۴:** Twilio از ۵۶۹M+ block و ۶۲٫۷M+ دلار explicit savings گزارش داد؛ روش محاسبه و audit خارجی منتشر نشده است. **FACT (خوداظهاری شرکت)** [S08]

## مسئله و داده‌های شناخته‌شده

- SMS pumping از فیلد ورود شماره برای OTP یا SMS سوءاستفاده می‌کند، پیام را به شماره‌های تحت‌کنترل مهاجم هدایت می‌کند و می‌تواند برای کسب‌وکار ارسال‌کننده هزینهٔ معنادار بسازد. **FACT** [S02] [S03]
- Twilio پیش از/همراه حفاظت درون‌محصولی، rate limit، geo permissions و bot defense مانند CAPTCHA را به‌عنوان mitigationهای مشتری‌مدار مطرح کرده بود. **FACT** [S03]
- این کنترل‌ها نیازمند کار عملیاتی و تصمیم مشتری هستند و پاسخ کاملاً خودکار نیستند. **FACT** [S03]
- اینکه بار عملیاتیِ کنترلهای مشتری‌مدار مستقیماً adoption یک حفاظت درون‌محصولی را افزایش دهد، **INFERENCE** است؛ شواهد منتشرشده causal test آن را ارائه نمی‌کنند. [S03]

## مکانیزم محصولِ مستند در مواد بعدی/فعلی

- مستندات بعدی/فعلی می‌گویند محصول ترافیک مورد انتظار، جاری و تاریخی و رفتار غیرعادی مقصد را بررسی می‌کند، دادهٔ رفتاری را با الگوهای شناخته‌شدهٔ fraud ترکیب می‌کند و پیش از ارسال SMS، destination prefix مشکوک را block می‌کند. **FACT** [S04] [S07]
- مستندات بعدی/فعلی سه شدت حفاظت را توصیف می‌کنند: Basic محتاطانه، Standard میانه و Max تهاجمی است. **FACT** [S04] [S07]
- راهنمای ۲۰۲۴، false-positive کمتر از ۰٫۱٪، ۱٪ و ۲٪ را به‌ترتیب برای Basic، Standard و Max بیان می‌کند. این‌ها target/claimهای Twilio هستند و نتیجهٔ audit مستقل نیستند. **FACT** [S07]
- مستندات بعدی/فعلی customer-controlهایی شامل تغییر سطح خدمت یا opt-out، Safe List، override در هر درخواست با RiskCheck، کنترل کشوری با geo permissions و fallbackها را توصیف می‌کنند. **FACT** [S04]
- همان مستندات observability شامل email alert، log درخواست block‌شده، error code 60410 و dashboard با allowed/blocked attempts، success rate، estimated savings، روند کشور و conversion را توصیف می‌کنند. **FACT** [S04]
- تاریخ عمومیِ معرفی یا در دسترس‌شدن هر یک از protection modeها، Safe List، RiskCheck، geo permissions، fallbackها یا ابزارهای observability در ۲۰۲۲ منتشر نشده است. **FACT: محدودیت شواهد** [S04] [S07]

## Who Said What

| گوینده | گفته/موضع | برچسب |
|---|---|---|
| Nader Attar، نویسندهٔ blog و PM veteran | در اعلام public beta، هدف را مقابله با fraud، بهبود verification conversion و کاهش maintenance دانست و از نتایج pilot محدود گفت. | **FACT: گزارش/موضع Twilio** [S02] |
| Nader Attar | دربارهٔ یک کسب‌وکار بزرگ social media ناشناس، افزایش ۲۷٪ conversion، کاهش ۴۲٪ cost per user، بیش از ۳۰۰هزار دلار صرفه‌جویی ماه نخست و ۱٫۵۷M دلار صرفه‌جویی مورد انتظار را گزارش کرد. نام مشتری و روش counterfactual افشا نشده است. | **FACT: ادعای شرکت با محدودیت شواهد** [S02] |
| Michael Piccirilli، data science leader | false positive را پرسش محوری خواند، از near-zero tolerance گفت و مواردی با کاهش تا ۳۵٪ هزینهٔ روزانه و conversion تا دو برابر را گزارش کرد. | **FACT: موضع/ادعای Twilio** [S03] |
| Khozema Shipchandler، President of Twilio Communications | گفت Fraud Guard در یک expansion deal با یک شرکت employment پیشرو instrumental بوده است؛ ارزش قابل انتساب deal افشا نشده است. | **FACT: اظهارنظر مدیریت** [S05] |

## بازار و فضای راه‌حل

- Twilio SMS pumping را مسئله‌ای industry-wide برای providerها و کسب‌وکارهای دارای phone-number field و OTP flow توصیف می‌کند؛ این یک characterization شرکتی است، نه market-size estimate مستقل. **FACT** [S03] [S07]
- راه‌حل‌های مجاورِ توصیف‌شده توسط Twilio شامل حفاظت embedded برای Verify، حفاظت برای Programmable Messaging و risk score در Lookup است که در آن مشتری threshold allow/block را انتخاب می‌کند. **FACT** [S07]
- برای competitor-by-competitor comparison قابل اتکا، شواهد عمومیِ بررسی‌شده کافی نیست. **ANALYSIS**

## تعارض‌ها و تفسیر محتاطانه

1. **ابهام chronology:** پست ۱۴ ژوئیه public beta را بیان می‌کند، changelog ۲۵ ژوئیه آن را beta می‌نامد و پست ۶ سپتامبر public beta را اعلام می‌کند. record عمومی تمایز دقیق این تاریخ‌ها را توضیح نمی‌دهد. **FACT: تعارض/ابهام در record** [S01] [S02] [S03]
2. **تغییر default:** مستندات فعلی می‌گویند قابلیت برای همهٔ مشتریان Verify به‌طور پیش‌فرض روشن است، اما material سال ۲۰۲۲ از enable در Console سخن می‌گوید. این از evolution بعدی پشتیبانی می‌کند، اما تاریخ تغییر default معلوم نیست. **FACT با محدودیت زمانی** [S02] [S04]
3. **تخصیص decision rights:** اینکه Twilio عمداً بین حفاظت خودکار Verify، کنترل‌های configurable و Lookup score اختیار تصمیم را تقسیم کرده، یک تفسیر portfolio است و rationale داخلیِ افشاشده نیست. **INFERENCE** [S04] [S07]

## شکاف‌های شواهد

- featureهای مدل، architecture، training data، weights، thresholdها، human review، cadence به‌روزرسانی و retention rules منتشر نشده‌اند.
- شمار و انتخاب مشتریان pilot، کنترل، statistical significance و روش time-normalized outcomes منتشر نشده‌اند. [S02]
- false-negative، precision، recall، false-positive aggregate بر حسب geography و validation شخص ثالث منتشر نشده‌اند. [S07]
- تاریخ گذار beta به GA، تاریخ معرفی protection modeها و کنترل‌ها، سهم انتخاب هر سطح، میزان استفاده از exceptionها، نرخ سوءاستفاده پس از override و میزان payout creditها در دسترس نیست. [S04] [S06] [S07]

## Sources

- [S01] Twilio، *Verify Automatic SMS Fraud Detection is in Beta*، 2022-07-25: https://www.twilio.com/en-us/changelog/verify-automatic-sms-fraud-detection-is-in-beta
- [S02] Nader Attar / Twilio، *Twilio Verify’s Automatic SMS Fraud Detection is now in Public Beta*، 2022-09-06: https://www.twilio.com/en-us/blog/products/launches/announcing-automatic-sms-fraud-detection-public-beta
- [S03] Michael Piccirilli / Twilio، *Reduce OTP Fraud with Twilio Verify’s Fraud Detection*، 2022-07-14: https://www.twilio.com/en-us/blog/developers/best-practices/verify-otp-fraud-detection
- [S04] Twilio Docs، *Verify Fraud Guard*: https://www.twilio.com/docs/verify/preventing-toll-fraud/sms-fraud-guard
- [S05] Twilio Investor Relations، *Q2 2023 Prepared Remarks - FINAL*، 2023-08-08: https://investors.twilio.com/static-files/9fa39db9-e450-4f25-b9bb-c2a8f551305a
- [S06] Twilio Legal، *Verify Fraud Guard*، 2024-07-10: https://www.twilio.com/en-us/legal/service-country-specific-terms/verify-fraud-guard
- [S07] Twilio، *Preventing SMS Pumping Fraud: A Guide to Our Protective Offerings*، 2024-08-08: https://www.twilio.com/en-us/blog/developers/best-practices/sms-pumping-protection-options
- [S08] Twilio Investor Relations، *Twilio annual-report material reporting AI product metrics*: https://investors.twilio.com/static-files/d19ba297-193c-4a92-b9cb-ce9a17f55c60
