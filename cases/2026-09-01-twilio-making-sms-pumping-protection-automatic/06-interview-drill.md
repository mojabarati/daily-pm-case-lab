# Interview Drill

## Main Questions

1. مسئلهٔ SMS pumping را چگونه از «کاهش هزینه» به یک مسئلهٔ چندذی‌نفعی Trust & Safety تبدیل می‌کنید؟
2. چرا comparison قبل/بعد برای سنجش موفقیت یک intervention ضد-fraud کافی نیست؟
3. بین intervention سراسری، risk score advisory و کنترل مشتری‌مدار چگونه انتخاب می‌کنید؟
4. MVP شما چیست و کدام قابلیت‌ها را عمداً به Post-MVP منتقل می‌کنید؟
5. اگر یک مشتری بزرگ به خاطر false positive احتمالی مخالف rollout باشد، چگونه تصمیم می‌گیرید؟

## Follow-up Questions

1. primary metric شما دقیقاً چه numerator و denominatorی دارد؟ چرا هزینهٔ پیام‌های block‌شده فقط metric توصیفی است و چگونه هزینهٔ واقعی هر تلاش واجد شرایط را میان treatment و holdout مقایسه می‌کنید؟
2. چه کسی label suspicious/fraud را adjudicate می‌کند، چگونه از score سیستم کور می‌ماند و unknownها چگونه گزارش می‌شوند؟
3. اگر aggregate completion ثابت بماند اما یک کشور افت شدید در start-to-completion یا افزایش abandonment داشته باشد، چه می‌کنید؟
4. چرا block count به‌تنهایی success metric بدی است؟
5. حداقل precision، حداکثر unknown-label share، confidence/power و روش کنترل آزمون‌های متعدد شما چیست؟ اگر یک segment sample کافی ندارد، چه تصمیمی می‌گیرید؟
6. چه داده‌هایی را به دلیل privacy یا misuse در dashboard مشتری نشان نمی‌دهید؟
7. چگونه میان customer override و حفظ efficacy ضد-fraud تعادل برقرار می‌کنید؟

## Challenge Questions

1. فرض کنید هزینهٔ افزایشیِ اجتناب‌شده مثبت است، اما Support-contact rate دو برابر و abandoned-session rate در یک segment بیشتر شده است. rollout را ادامه می‌دهید، pause می‌کنید یا iterate؟ با چه segmentation و thresholdی؟
2. فرض کنید مهاجمان رفتارشان را تغییر می‌دهند و precision adjudicated افت می‌کند. چه بخش‌هایی از system باید adaptive باشد و چه چیزهایی نباید برای مهاجم آشکار شود؟
3. یک تیم sales خواهان guarantee مالی زودهنگام است، ولی false-negative rate و نرخ unknown هنوز ناشناخته است. recommendation شما چیست؟
4. مشتری حاضر به treatment/holdout نیست، زیرا نمی‌خواهد بخشی از traffic بدون action جدید بماند. چگونه رضایت، shadow mode و قابلیت تعمیم نتایج را مدیریت می‌کنید؟

# Evaluation Rubric

| بُعد | ضعیف | خوب | عالی |
|---|---|---|---|
| Framing | مسئله را صرفاً «ساخت مدل» می‌بیند | مشتری و کاربر را می‌بیند | economics، trust، API experience و uncertainty را یکپارچه می‌کند |
| Customer/Business Understanding | فقط هزینه را ذکر می‌کند | completion و burden را اضافه می‌کند | segmentهای مشتری، unit economics، support و risk-sharing را تفکیک می‌کند |
| Reasoning | با فرض‌های پنهان نتیجه می‌گیرد | فرض‌ها را بیان می‌کند | FACT، INFERENCE، label uncertainty و دادهٔ لازم برای falsify کردن hypothesis را جدا می‌کند |
| Prioritization | فهرست قابلیت می‌دهد | MVP و roadmap دارد | smallest reversible intervention را با dependency و learning value اولویت می‌دهد |
| Metrics | metricهای مبهم مانند «کاهش fraud» | metricهای قابل شمارش | outcome مشترک treatment/holdout، definition، baseline، window، segmentation، adjudication، unknown rate و threshold logic دارد |
| Trade-offs | false positive را نادیده می‌گیرد | trade-off را نام می‌برد | guardrailهای completion، retry، abandonment، exception abuse، privacy و latency را مدیریت می‌کند |
| Execution | rollout کلی می‌گوید | canary و monitoring دارد | shadow mode، رضایت treatment/holdout، adjudication کور، kill switch، توان آماری، multiplicity handling و maturity window طراحی می‌کند |
| Communication | jargon و پاسخ پراکنده | ساختار روشن | recommendation صریح، uncertainty شفاف و تصمیم قابل دفاع برای stakeholderهای مختلف ارائه می‌کند |

## روش تمرین

برای هر پاسخ، ابتدا در ۳۰ ثانیه مسئله و recommendation را بگویید؛ سپس در ۲ دقیقه metric، روش adjudication، guardrail و experiment را توضیح دهید. در پایان، یک assumption خود را نام ببرید که اگر غلط باشد recommendation شما تغییر می‌کند.
