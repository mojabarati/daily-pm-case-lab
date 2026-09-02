# Model Answer — پاسخ مستقل در cutoff

> این پاسخ در پایان ۱۳ ژوئیهٔ ۲۰۲۲ نوشته شده است. بنابراین، طراحی زیر یک recommendation مستقل است و ادعا نمی‌کند که Twilio بعداً دقیقاً همین کار را انجام داده است. هر عدد، مدت، حجم cohort، threshold، سطح confidence، توان آماری یا dependency که شواهد عمومیِ cutoff ندارد، **scenario assumption** است.

## ۱) Problem framing

برای مشتری، مسئله «هزینهٔ پیام‌های غیرمشروع بدون تخریب completion کاربران واقعی» است. برای کاربر نهایی، مسئله «دریافت به‌موقع و قابل اتکای verification» است. برای Twilio، مسئله هم Trust & Safety و هم سلامت economics و اعتماد به Verify است.

**فرضیهٔ اصلی — INFERENCE:** بخشی از spikes هزینه ناشی از misuse هدفمند شماره‌هاست، نه صرفاً رشد مشروع یا تغییر traffic mix. پیش از intervention باید این فرضیه آزموده شود.

## ۲) بازیگران و symptomها

| بازیگر | symptom/نیازِ سناریویی |
|---|---|
| customer developer | integration ساده، کنترل policy و هزینهٔ قابل پیش‌بینی |
| end user مشروع | completion سریع و مسیر recovery در رخداد خطا |
| finance/ops مشتری | تشخیص spike، attribution و اقدام سریع |
| Trust & Safety Twilio | مداخله مؤثر با false positive کم |
| Support/Legal | explanation، audit trail و policy قابل اجرا |
| مهاجم | انگیزه برای عبور از کنترل‌ها؛ مدل رفتاری او نامعلوم است |

## ۳) hypothesisها و دادهٔ موردنیاز

1. **H1:** concentration غیرعادی در destination/route/customer نشانهٔ misuse است.
2. **H2:** بخشی از traffic ظاهراً غیرعادی، legitimate event-driven traffic است.
3. **H3:** friction کنترل‌های دستی باعث می‌شود مشتریان دیر واکنش دهند.

برای آزمون، event-level data لازم است: زمان درخواست، account، geography، destination representation ایمن و حداقل‌سازی‌شده، channel، send outcome، verification completion، هزینه، retry، session/device/bot signal در صورت مجازبودن، support dispute و configuration. retention، access control و legal basis داده باید پیش از اجرا توسط Legal/Privacy تأیید شود.

**دادهٔ بالقوه گمراه‌کننده:** raw block count، مجموع هزینه و conversion aggregate؛ زیرا تغییر mix کشور، seasonality، customer growth یا outage می‌تواند این‌ها را جابه‌جا کند.

## ۴) گزینه‌ها و مقایسه

| گزینه | مزیت | هزینه/ریسک | تصمیم |
|---|---|---|---|
| documentation برای rate limit/CAPTCHA | سریع، کم‌هزینه | burden و کیفیت اجرا به مشتری منتقل می‌شود | baseline، نه راه‌حل کافی |
| rules ثابت در سطح جهانی | MVP بسیار ساده | bypass و false positive در segmentهای متفاوت | رد برای rollout گسترده |
| risk score advisory | autonomy زیاد | مشتری باید policy و عملیات بسازد | گزینهٔ enterprise بعدی |
| intervention پیش از send با confidence tier و customer controls | جلوگیری زودهنگام و تجربهٔ ساده‌تر | false positive، پیچیدگی policy و پشتیبانی | توصیه برای MVP محدود |
| هیچ تغییر جدید | ساده و بدون risk مداخلهٔ جدید | هزینه یا ترافیک غیرعادی ممکن است بدون پاسخ محصولی بماند | baseline آزمایشی |

## ۵) Recommendation و MVP

### Recommendation

یک **pre-send risk intervention** داخل Verify بسازید که ابتدا فقط در cohort محدود عمل می‌کند. قواعد یا مدل باید score confidence تولید کنند؛ action اولیه برای high-confidence caseها محدودسازی ارسال است و برای confidenceهای پایین‌تر فقط observability فراهم می‌شود. انتخاب model و threshold قطعی نیست؛ با pilot calibrate می‌شوند.

### MVP

- event pipeline با privacy review؛
- rules اولیهٔ قابل ممیزی برای high-confidence anomaly؛
- feature flag در سطح account و geography؛
- response/error semantics پایدار برای مشتری؛
- customer notification و log قابل export؛
- مسیر support برای disputed case؛
- fallback channel فقط اگر customer پیشاپیش آن را پیاده‌سازی کرده باشد.

### Non-goals

- تضمین حذف کامل fraud؛
- تصمیم‌گیری انسانی برای هر request؛
- وعدهٔ جبران مالی؛
- یک threshold جهانی ثابت؛
- ساختن bot defense کامل برای اپلیکیشن مشتری.

### Post-MVP

پس از سنجش کیفیت، calibration برحسب customer/geography، policy tierهای قابل انتخاب، recommendation برای configuration، review automation و سپس بررسی اقتصادیِ هر گونه guarantee را بررسی می‌کنم. این‌ها **ANALYSIS** هستند و به نتایج MVP وابسته‌اند.

## ۶) Metrics، برچسب‌گذاری و معیارهای تصمیم

### اصل اندازه‌گیری

نباید ادعا کنیم پیام block‌شده واقعاً fraud بوده است، زیرا پیام ارسال نشده و outcome مشاهده‌پذیرِ مستقیم ندارد. بنابراین، هزینهٔ پیام‌های block‌شده فقط یک metric عملیاتی و توصیفی است:

`Blocked-message cost exposure = مجموع هزینهٔ ثبت‌شده یا برآوردشدهٔ sendهایی که intervention متوقف کرده است`

این معیار حجم مداخله را نشان می‌دهد و **metric موفقیت اصلی نیست**؛ با افزایش تعداد interventionها به‌صورت مکانیکی بالا می‌رود.

### Primary metric: هزینهٔ افزایشیِ اجتناب‌شده به‌ازای هر تلاش واجد شرایط

**تعریف عملیاتی — ANALYSIS:**

`Incremental avoided eligible-message cost per eligible attempt = میانگین هزینهٔ پیام‌های واجد شرایط در holdout − میانگین هزینهٔ پیام‌های واجد شرایط در treatment`

- **واحد تحلیل:** هر تلاش واجد شرایط Verify که پیش از randomization تعریف و ثبت شده است؛ تلاش‌های تکراری نیز طبق یک قانون از پیش ثبت‌شده به session یا attempt منتسب می‌شوند. **Scenario assumption**
- **هزینه در treatment:** هزینهٔ واقعی پیام‌های ارسال‌شده پس از اعمال policy جدید، به‌ازای همهٔ تلاش‌های واجد شرایط treatment؛ پیامِ محدودشده هزینهٔ ارسالِ صفر در این outcome دارد.
- **هزینه در holdout:** هزینهٔ واقعی پیام‌های ارسال‌شده تحت policy پیشین یا بدون action جدید، به‌ازای همهٔ تلاش‌های واجد شرایط holdout.
- **مقایسهٔ مشترک:** هر دو بازو outcome یکسانِ «هزینهٔ واقعی پیام‌های واجد شرایط به‌ازای تلاش واجد شرایط» دارند؛ بنابراین کاهش هزینه در treatment با حجم block به‌تنهایی تعریف نمی‌شود.
- **randomization:** تخصیص treatment/holdout درون strata از پیش تعیین‌شدهٔ account × geography × use case، در صورت وجود، انجام می‌شود. در holdout، score و action پیشنهادی به‌صورت shadow log ثبت می‌شود تا نرخ اقدام پیشنهادی و drift قابل مشاهده باشد، اما score برای محاسبهٔ primary metric لازم نیست. **Scenario assumption**
- **baseline:** میانگین holdout هم‌زمان، نه مقایسهٔ قبل/بعد. برای مشتری یا segmentی که holdout ندارد، هیچ ادعای causal ثبت نمی‌شود.
- **تفسیر:** این metric کاهش هزینهٔ ارسال را می‌سنجد، نه مقدار fraud تأییدشده و نه savings تحقق‌یافتهٔ مشتری پس از همهٔ آثار جانبی.
- **evaluation window:** **Scenario assumption:** ۲۸ روز exposure. پنجره باید پیش از شروع قفل شود و برای هر دو بازو یکسان باشد.

### فرایند adjudication پیشنهادی — ANALYSIS

- تیم fraud operations نمونه‌ای تصادفی و طبقه‌بندی‌شده از requestهای treated، holdout و shadow را بررسی می‌کند؛ نمونه‌گیری باید confidence band، geography و customer segment را پوشش دهد.
- reviewer به score، rule identifier و assignment درمان/holdout دسترسی ندارد تا label leakage کاهش یابد.
- label بر پایهٔ شواهد مجازِ پس از رخداد تعریف می‌شود: الگوی تکرار، سیگنال‌های bot در صورت مجازبودن، dispute مشتری، completion و retry، و سایر شواهد عملیاتیِ از پیش مستندشده. هر موردی که شواهد کافی ندارد **unknown** می‌ماند، نه fraud.
- برای requestهای block‌شده، نبود ارسال به معنی fraud نیست. آن‌ها censored هستند و با evidenceهای پس از request، نمونهٔ shadow هم‌الگو و adjudication کور ارزیابی می‌شوند.
- labelهای تأخیری در یک پنجرهٔ maturation نگه داشته می‌شوند. هر metric کیفیت باید نرخ unknown و نرخ عدم‌تکمیل label را نیز گزارش کند.

این فرایند یک **پیشنهاد اجرایی** است، نه ادعا دربارهٔ فرایند تاریخی Twilio.

### Metricهای مکمل

1. **Adjudicated precision of intervention** = interventionهای دارای label fraud/suspicious تأییدشده / interventionهای دارای label نهایی. نرخ unknown جداگانه گزارش می‌شود.
2. **Legitimate start-to-completion rate** = sessionهای eligible که از start به completion موفق می‌رسند / sessionهای eligible که verification را شروع کرده‌اند.
3. **Retry-loop rate** = sessionهایی با retry بیش از الگوی baseline / sessionهای eligible. تعریف «بیش از الگوی baseline» باید پیش از آزمایش ثبت شود. **Scenario assumption**
4. **Abandoned verification-session rate** = sessionهای شروع‌شده که تا پایان پنجرهٔ از پیش تعیین‌شده نه completion دارند و نه مسیر جایگزین ثبت‌شده / sessionهای شروع‌شده. این metric باید برای treated و holdout و در سطح segment گزارش شود.
5. **Alternative-channel usage rate** = sessionهای verification که از channel جایگزینِ از پیش موجود مشتری استفاده می‌کنند / sessionهای eligible؛ افزایش آن می‌تواند نشانهٔ اصطکاک باشد و علت را اثبات نمی‌کند.
6. **Time-to-detection** = median زمان از شروع anomaly تا action؛ با policy پیشین مقایسه می‌شود.
7. **Customer operational burden** = تعداد تغییر configuration، ticket و زمان عملیات گزارش‌شده به ازای هر ۱۰هزار attempt؛ denominator و روش ثبت زمان باید پیش از اجرا تثبیت شود. **Scenario assumption**

### آستانه‌های از پیش ثبت‌شده — Scenario assumptions

هیچ نرخ تاریخیِ precision، unknown، حجم نمونه یا توان آماری در packet وجود ندارد. برای executable بودن تصمیم، پیش از canary موارد زیر ثبت می‌شوند:

- **Precision:** حد پایینِ بازهٔ اطمینان ۹۵٪ برای adjudicated precision در cohort قابل گسترش، دست‌کم ۹۰٪ باشد.
- **Unknown-label share:** سهم unknown در نمونهٔ adjudication از ۲۰٪ بیشتر نباشد؛ اگر بیشتر باشد، کیفیت تصمیم برای continue قابل تفسیر نیست، حتی اگر primary metric مثبت باشد.
- **توان و confidence:** طراحی نمونه باید برای تشخیص حداقل اثر اقتصادیِ از پیش ثبت‌شده با توان حداقل ۸۰٪ و بازهٔ اطمینان ۹۵٪ انجام شود. اگر حجم sample کافی نشود، نتیجه «inconclusive» است، نه continue.
- **آزمون‌های segment:** account/geography/use-caseهای rollout از پیش تعیین می‌شوند. برای مجموعهٔ آزمون‌های تصمیم‌گیریِ هم‌خانواده، اصلاح Holm اعمال می‌شود. segmentهایی که توان کافی ندارند گسترش نمی‌یابند، حتی اگر estimate نقطه‌ای آن‌ها مثبت باشد.
- **کالیبراسیون:** مقادیر ۹۰٪، ۲۰٪، ۸۰٪ و ۹۵٪ هدف‌های پیشنهادی‌اند، نه fact؛ پس از shadow mode با تحمل risk مشتری، هزینهٔ خطا و ظرفیت adjudication بازبینی می‌شوند، اما هر تغییر پیش از مشاهدهٔ نتایج مرحلهٔ بعد ثبت می‌شود.

## ۷) Guardrail Metrics

1. **Completion delta:** اختلاف start-to-completion rate میان treatment و holdout، در هر segment.
2. **Silent-abandonment delta:** اختلاف abandoned verification-session rate میان treatment و holdout، در هر segment؛ این guardrail کاربران مشروعی را که شکایت نمی‌کنند پوشش می‌دهد.
3. **Retry-loop delta:** اختلاف retry-loop rate میان treatment و holdout، در هر segment.
4. **Alternative-channel delta:** تغییر استفاده از channel جایگزین در treatment نسبت به holdout، فقط در مشتریانی که چنین channelی را پیشاپیش دارند.
5. **False-positive proxy rate:** interventionهایی که ظرف پنجرهٔ از پیش تعریف‌شده با evidence معتبر به‌عنوان درخواست مشروع adjudicate یا dispute/recovered می‌شوند / کل interventionها.
6. **Support-contact rate:** ticketهای مرتبط با intervention به ازای ۱۰هزار attempt، treatment در برابر holdout.
7. **Latency:** p95 latency افزوده‌شده در Verify API؛ مقایسه با pre-feature baseline در همان region.

**منطق thresholdها — Scenario assumptions:** pause خودکار برای هر segmentی که پس از اصلاح آزمون‌های چندگانه، حد بالای بازهٔ اطمینان ۹۵٪ آن نشان دهد completion بیش از ۰٫۵ percentage point پایین‌تر از holdout است، یا false-positive proxy از ۰٫۲٪ عبور می‌کند. این مقادیر پس از shadow mode، با نرخ طبیعی retry/dispute، حجم sample و تحمل risk مشتری calibrate می‌شوند. اگر sample کم باشد، تصمیم قطعی گرفته نمی‌شود و window طولانی‌تر می‌شود.

## ۸) Experiment و rollout

1. **Shadow mode — scenario assumption: ۷ روز:** score و recommended action log می‌شوند، اما هیچ پیام محدود نمی‌شود. هدف، data quality، distribution score، نرخ unknown و برآورد اولیهٔ retry/abandonment است.
2. **Canary — scenario assumption: ۱۴ روز:** accountهای opt-in با high-confidence action، random holdout درون همان segment و kill switch account-level.
3. **Staged rollout — scenario assumption: ۲۸ روز exposure + ۱۴ روز maturation label:** exposure فقط برای segmentهایی افزایش می‌یابد که primary metric، precision adjudicated، unknown-label threshold و guardrailها را پاس کرده‌اند. monitoring روزانه و review دوره‌ای توسط PM، DS، T&S، Support و Legal انجام می‌شود.
4. **Scale:** فقط پس از maturation label، گزارش نرخ unknown، بررسی segment-level harm و کفایت توان آماری. rollout هم‌زمان جهانی انجام نمی‌شود.

## ۹) Dependencies و riskها

| risk | mitigation پیشنهادی | مالک dependency پیشنهادی |
|---|---|---|
| false positive و آسیب کاربر مشروع | conservative first action، holdout، kill switch، مسیر dispute و سنجش abandonment/retry | T&S + Product + Support |
| label bias یا censored event | adjudication کور، گزارش unknown، نمونه‌گیری طبقه‌بندی‌شده | Fraud Operations + Data Science |
| model/rule drift | monitoring distribution و review دوره‌ای | Data Science |
| privacy/data misuse | data minimization، retention policy، access audit | Legal/Privacy + Security |
| attacker adaptation | عدم افشای ruleهای حساس، monitoring برای pattern shift | Security + T&S |
| API breaking change | versioned error semantics و migration guide | Engineering + Developer Experience |
| support overload | cohort کوچک، playbook و escalation path | Support |
| customer mistrust | توضیح روشنِ opt-in، holdout و actionهای قابل مشاهده | Product + GTM |

## ۱۰) Kill / continue / iterate criteria

- **Continue:** primary metric در پنجرهٔ قفل‌شده، کاهش هزینهٔ افزایشیِ statistically credible در برابر holdout نشان دهد؛ حد پایین بازهٔ اطمینان ۹۵٪ آن بالاتر از صفر باشد؛ precision و unknown-label share به آستانه‌های از پیش ثبت‌شده برسند؛ هیچ segment دارای توان کافی guardrail را نقض نکند؛ و p95 latency از بودجهٔ توافق‌شده با Engineering تجاوز نکند. هر مقدار عددیِ بودجه یا آستانه، **scenario assumption** است.
- **Iterate:** primary metric مثبت باشد، اما precision پایین، unknown rate بالا، support contact بالا، retry-loop بالا یا یک segment دچار completion/abandonment delta نامطلوب شود. rule یا threshold فقط برای همان segment بازتنظیم و canary تکرار می‌شود؛ بازتنظیم باید پیش از آزمون بعدی ثبت شود.
- **Kill/Pause:** هر breach guardrail در segment دارای توان کافی، نشانهٔ privacy/security incident، یا نتیجهٔ inconclusive پس از پنجرهٔ کامل maturity و ظرفیت نمونه‌گیریِ از پیش برنامه‌ریزی‌شده. در این حالت action جدید خاموش می‌شود و logging ایمن برای root-cause analysis باقی می‌ماند. مشتری از کنترل‌های موجود خود، در صورت availability، استفاده می‌کند یا یک مسیر manual mitigation مستند دریافت می‌کند.

این recommendation عمداً موفقیت را با تعداد actionها نمی‌سنجد: intervention بیشتر می‌تواند هم نشانهٔ پوشش بهتر و هم نشانهٔ false positive بیشتر باشد.
