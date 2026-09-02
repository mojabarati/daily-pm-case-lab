# Twilio چه کرد؟

## تصمیم مستند

Twilio حفاظت را به‌صورت یک قابلیت خودکار و بدون هزینهٔ اضافی در Verify عرضه کرد. **FACT** [S01] [S02]

طبق مستندات بعدی/فعلی، قابلیت ترافیک مورد انتظار، جاری و تاریخی و رفتار غیرعادی مقصد را تحلیل می‌کند، دادهٔ رفتاری و fraud schemeهای شناخته‌شده را ترکیب می‌کند و پیش از ارسال، destination prefix مشکوک را block می‌کند. **FACT** [S04] [S07]

## توالی و rollout

1. Twilio می‌گوید ابتدا pilot محدودی با مشتریان اجرا کرد؛ اما جزئیات cohort و design آزمایش را منتشر نکرد. **FACT** [S02]
2. تا ۱۴ ژوئیهٔ ۲۰۲۲، پست Twilio وضعیت public beta را بیان کرد. **FACT** [S03]
3. changelog در ۲۵ ژوئیه beta را اعلام کرد و پست ۶ سپتامبر public beta و enablement در Console را معرفی کرد. **FACT** [S01] [S02]
4. record عمومی تفاوت دقیق میان این سه تاریخ را روشن نمی‌کند. **FACT: ابهام شواهد** [S01] [S02] [S03]
5. مستندات فعلی از روشن‌بودن پیش‌فرض برای همهٔ مشتریان Verify حکایت دارد، ولی تاریخ این تغییر منتشر نشده است. **FACT با محدودیت تاریخی** [S04]

## پیکربندی و عملیات در مستندات بعدی/فعلی

- مستندات بعدی/فعلی Basic، Standard و Max را توصیف می‌کنند: از block محتاطانه تا تهاجمی. **FACT** [S04] [S07]
- همان مستندات از Safe List، RiskCheck per-request، geo permissions، تنظیم سطح خدمت یا opt-out و fallbackهای کانالی نام می‌برند. **FACT** [S04]
- برای عملیات و بررسی، مستندات بعدی/فعلی email alert، Verify Logs، error 60410 و Fraud Insights با attempts، success rate، estimated savings، روند کشور و conversion را توصیف می‌کنند. **FACT** [S04]
- public record تاریخ معرفی یا availability این modeها، کنترل‌ها و ابزارهای عملیات را در rollout سال ۲۰۲۲ مشخص نمی‌کند. **FACT: محدودیت شواهد** [S04] [S07]
- **INFERENCE، نه rationale عمومیِ تأییدشده:** این portfolio احتمالاً میان حفاظت خودکار و استثناهای business-specific اختیار توزیع می‌کند. مستندات rationale داخلی Twilio را افشا نمی‌کنند. [S04] [S07]

## ریسک‌پذیری اقتصادی

Twilio در شرایط ۲۰۲۴ خود یک credit promise مشروط ارائه کرد: برای پیام‌های pumping-fraud واجد شرایطی که باید block می‌شدند، Fraud Guard باید فعال و در Max Protection Mode نگه داشته می‌شد؛ claim window، review و شروط eligibility نیز وجود داشت. **FACT** [S06]

فعال‌سازی Geo Permissions، Safe List یا RiskCheck برای شماره‌های آسیب‌دیده می‌تواند detection ترافیک مصنوعی را مختل کند و آن پیام‌ها را از credit promise خارج کند. **FACT** [S06]

## نتایج گزارش‌شده

- یک مشتری social-media ناشناس که OTP traffic را به Verify منتقل کرد، بنا به گزارش Twilio، ۲۷٪ افزایش SMS conversion، ۴۲٪ کاهش cost per user، بیش از ۳۰۰هزار دلار صرفه‌جویی ماه اول و ۱٫۵۷M دلار صرفه‌جویی مورد انتظار داشته است. روش counterfactual و هویت مشتری منتشر نشده‌اند. **FACT: ادعای شرکت با قابلیت راستی‌آزمایی محدود** [S02]
- Twilio در ۲۰۲۲ مواردی با کاهش تا ۳۵٪ spend روزانه و conversion تا دو برابر در مناطق مشخص گزارش کرد؛ denominator و روش اندازه‌گیری منتشر نشده‌اند. **FACT: ادعای شرکت با محدودیت شواهد** [S01] [S03]
- Twilio از ۵۶۹M+ block و ۶۲٫۷M+ دلار explicit savings از ژوئن ۲۰۲۲ تا اکتبر ۲۰۲۴ گزارش کرد؛ methodology و audit خارجی منتشر نشده‌اند. **FACT: خوداظهاری شرکت** [S08]
- مدیریت گفت محصول در یک expansion deal نقش instrumental داشته، اما ارزش deal منتسب به محصول افشا نشده است. **FACT** [S05]
