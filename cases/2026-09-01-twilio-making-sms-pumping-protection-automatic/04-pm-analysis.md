# PM Analysis

## ۱) صورت مسئله

مسئله فقط «تشخیص fraud» نیست؛ مسئله یک API trade-off است: ارسال پیام مشکوک می‌تواند هزینهٔ مشتری را افزایش دهد، اما ممانعت از ارسال ممکن است verification کاربر مشروع را مختل کند. مکانیزم SMS pumping و هزینه‌سازبودن آن **FACT** است. [S02] [S03] اینکه هر block لزوماً conversion را بهبود می‌دهد، **INFERENCE** است و باید با counterfactual سنجیده شود.

## ۲) Root cause

دادهٔ عمومی، root cause فنیِ مدل یا سهم نسبیِ attack vectorها را منتشر نمی‌کند؛ پس نمی‌توان یک ضعف مشخصِ implementation قبلی را به Twilio نسبت داد. **FACT: شواهد عمومی ناکافی است.**

با این حال، **ANALYSIS:** در سطح product-system، اتکای صرف به rate limit، geo permissions و bot control کنترل را به مشتری منتقل می‌کند و ممکن است در محیط‌های ناهمگون به configuration burden بینجامد. وجود این controlها **FACT** است؛ پیامد علّی، inference است. [S03]

## ۳) استراتژی مشاهده‌شده

Twilio detection را در Verify عرضه کرد. مستندات بعدی/فعلی نیز protection modeهای قابل پیکربندی، exceptionها و observability را توصیف می‌کنند؛ تاریخ عمومیِ availability هر یک از این اجزا در rollout ۲۰۲۲ مشخص نیست. **FACT** [S01] [S02] [S04] [S07]

مواد مستند سه لایه را نشان می‌دهند:

1. **Prevention:** مداخله پیش از ارسال. **FACT** [S04] [S07]
2. **Control:** شدت‌های متفاوت و exceptionها در مستندات بعدی/فعلی. **FACT** [S04]
3. **Recovery/learning:** alert، log، error code و metrics برای بررسی در مستندات بعدی/فعلی. **FACT** [S04]

Twilio بعداً credit promise مشروطی ارائه کرد. **FACT** [S06]

## ۴) گزینه‌ها و اولویت‌بندی

| گزینه | مزیت | trade-off | ارزیابی |
|---|---|---|---|
| واگذاری کامل کنترل به مشتری | autonomy بالا | operational burden و کیفیت ناهمگون؛ بخش نخست FACT و بخش دوم ANALYSIS [S03] | مناسب مشتریان بسیار تخصصی، نه راه‌حل پایهٔ فراگیر |
| block سراسری و یکسان | ساده‌تر برای اجرا | false-positive risk و عدم تناسب با use caseها؛ ANALYSIS | پرریسک بدون calibration |
| حفاظت embedded با شدت قابل انتخاب و exception | تعادل میان scale، autonomy و controllability | complexity، configuration misuse و support cost؛ ANALYSIS | مواد بعدی/فعلی چنین اجزایی را مستند می‌کنند. [S04] [S07] |
| risk score صرفاً advisory | مشتری threshold را کنترل می‌کند | تصمیم و عملیات نزد مشتری می‌ماند؛ ANALYSIS | برای مشتریان با policy بالغ مناسب است |
| هیچ اقدام محصولی جدید | تغییر فنی و risk مداخله ندارد | هزینه و burden مشتری ممکن است باقی بماند؛ ANALYSIS | baseline لازم برای مقایسهٔ تصمیم |

اولویت‌بندی مشاهده‌شده ظاهراً بر کاهش friction برای مشتریان Verify استوار است؛ اما rationale داخلی و scoring framework منتشر نشده‌اند. **INFERENCE** [S01] [S02] [S04]

## ۵) Trade-offهای کلیدی طراحی

- **Fraud loss در برابر false positive:** شدت بالاتر، طبق نام‌گذاری محصول، block تهاجمی‌تری دارد. **FACT** [S04] [S07] رابطهٔ کمی میان شدت و loss/false negative منتشر نشده است.
- **Simplicity در برابر configurability:** Safe List، RiskCheck و geo settings flexibility می‌دهند. **FACT** [S04] اما exceptionها ممکن است efficacy detection را کاهش دهند؛ شرایط حقوقی این امکان را برای شماره‌های affected تصریح می‌کند. **FACT** [S06]
- **حفاظت در برابر accountability:** observability امکان بررسی می‌دهد. **FACT** [S04] اما هیچ public evidence از سرعت رسیدگی support یا کیفیت appeal flow منتشر نشده است.
- **ارزش رایگان در برابر exposure مالی:** قابلیت بدون هزینهٔ اضافی عرضه شد. **FACT** [S01] [S02] credit مشروط در ۲۰۲۴ نشان‌دهندهٔ risk-sharing محدود است. **FACT** [S06]

## ۶) Metrics و اجرا

Twilio در dashboard خود allowed/blocked attempts، success rate، estimated savings، country trend و conversion را در دسترس می‌گذارد. **FACT** [S04] این‌ها observability هستند، اما public record baseline، attribution method، precision/recall یا experiment design را ارائه نمی‌کند. **FACT: شواهد عمومی ناکافی است.**

**ANALYSIS:** metric tree مناسب باید سه سطح داشته باشد: (۱) تغییر هزینهٔ ارسال برای درخواست‌های واجد شرایط در treatment در برابر holdout، (۲) completion verification مشروع، و (۳) سلامت عملیات شامل latency، ticket rate و exception abuse. گزارش‌های aggregate block و savings برای اثبات causal efficacy کافی نیستند، زیرا denominator و counterfactual عمومی نیست. [S08]

## ۷) ریسک‌ها و second-order effects

- block اشتباه می‌تواند مانع ورود یا recovery کاربر شود. **ANALYSIS؛** Twilio نیز false-positive را یک موضوع مرکزی معرفی کرده است. [S03]
- exceptionها برای ترافیک business-critical مفیدند، اما می‌توانند سطح attack را تغییر دهند؛ impairment detection برای برخی exceptionها در شروط credit تصریح شده است. **FACT** [S06]
- تفاوت geography و customer segment می‌تواند calibration یکسان را ضعیف کند. **ANALYSIS؛** دادهٔ عمومیِ variation جغرافیایی منتشر نشده است.
- estimated savings ممکن است در فروش و اعتماد مفید باشد، اما اگر methodology شفاف نباشد، برداشت مشتری از آن با realized savings متفاوت شود. **ANALYSIS** [S04] [S08]

## What Could Have Been Done Better?

### الف) نقد evidence-backed

**ضعف مشاهده‌شده:** Twilio methodology مربوط به cohort، control group، selection criteria و statistical significance نتایج pilot را منتشر نکرده است. **FACT** [S02]

- **چرا مهم بود:** بدون counterfactual، خوانندهٔ عمومی نمی‌تواند علت نتایج conversion یا savings را جدا از mix مشتری، geography یا تغییرات هم‌زمان ارزیابی کند. **ANALYSIS** [S02]
- **جایگزین:** انتشار یک measurement note با cohort definition، evaluation window، denominator، confidence interval و محدودیت‌های attribution. **ANALYSIS**
- **فایدهٔ مورد انتظار:** تصمیم‌گیری آگاهانه‌تر مشتری و اعتماد بیشتر به claims. **ANALYSIS**
- **trade-off:** افشای بیشتر methodology ممکن است اطلاعات رقابتی یا حساسیت امنیتی ایجاد کند. **ANALYSIS**
- **risk:** مهاجمان ممکن است از جزئیات بیش از حد برای سازگارشدن استفاده کنند. **ANALYSIS**
- **validation:** سنجش کاهش disputeهای sales/support دربارهٔ attribution و افزایش activation در cohortهایی که note را دیده‌اند، با آزمایش پیام‌رسانی. **ANALYSIS**

### ب) plausible alternative؛ نه ضعف مشاهده‌شده

**شواهد عمومی برای ادعای ضعف در workflow اعتراض، زمان پاسخ support یا کیفیت explanation کافی نیست.**

- **جایگزین پیشنهادی — ANALYSIS:** یک appeal/review workflow با reason category حداقلی، SLA داخلیِ پیشنهادی و audit trail برای درخواست‌های disputed طراحی شود.
- **فایدهٔ مورد انتظار — ANALYSIS:** کاهش زمان بازیابی برای موارد business-critical و دادهٔ برچسب‌خوردهٔ بهتر برای تحلیل.
- **trade-off — ANALYSIS:** هزینهٔ عملیات و امکان social engineering.
- **risk — ANALYSIS:** مهاجم می‌تواند با volume زیاد capacity review را مصرف کند.
- **validation — ANALYSIS:** pilot با segment کوچک، اندازه‌گیری appeal rate، reversal rate، زمان resolution و abuse rate.

### ج) speculative counterfactual؛ نه نتیجه‌گیری دربارهٔ شرکت

**COUNTERFACTUAL:** اگر Twilio یک کنترل recommendation-based و country/customer calibration شفاف‌تر عرضه می‌کرد، شاید برخی مشتریان زودتر سطح مناسب risk خود را انتخاب می‌کردند. این ادعا قابل اثبات با record عمومی نیست؛ نه distribution انتخاب‌ها و نه outcome بر حسب segment منتشر نشده‌اند. [S04] [S07]

- **فایدهٔ مورد انتظار:** calibration سریع‌تر برای مشتریان heterogeneous. **COUNTERFACTUAL**
- **trade-off و risk:** افزایش choice overload، configuration error و سطح حمله. **COUNTERFACTUAL**
- **validation:** randomized onboarding با recommendation در برابر setup خنثی؛ مقایسهٔ false-positive proxy، fraud-cost proxy، support contact و تغییرات configuration در یک پنجرهٔ ثابت. **ANALYSIS**
