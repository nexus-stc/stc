const translations = {
  'en': {
    about: "About",
    about_alert: `
    <p>Standard Template Construct (STC) continues to evolve.</p> 
    <p>We have already transferred to STC:</p>
    <ul>
      <li>7 500 000 books</li>
      <li>More than 1 000 000 of recent scientific papers</li>
    </ul>
    <p>However, there remains a multitude of knowledge that requires preservation and unchaining. We want <b>individuals capable of hosting and seeding</b> terabytes of data to join us in our mission.</p>
    <p>If you are interested in seeding, please reach us using the contacts below.</p>
    <p>If you wish to aid the development of STC, kindly consider <a href="/#/donate">making a donation</a></p>
    `,
    about_end: `
    <p>The world has changed, and the humankind has evolved into a truly interconnected, digital specie. Traditional methods of knowledge management no longer suffice, and new approaches are necessary to accommodate this shift. The act of restricting knowledge is now more harmful than releasing it free or under copyleft licenses.</p>
    <p>The pace of liberating initiatives is too slow, and here we are, to help destruction of old, injust and improper chains.</p>
    `,
    about_intro: `
    <p>STC is a self-replicating search engine that grants sentient beings free and convenient access to knowledge discovered by the human race throughout its age of science and digital era.</p>
    <p>Founded in 2021 year (Earth Time, Gregorian Calendar), STC relies upon <a href="https://github.com/izihawa/summa">Summa</a>, <a href="https://webassembly.org/">WASM</a> and <a href="https://ipfs.tech/">IPFS</a> for its operation.</p>
    <p>STC is also a pure peer-to-peer system and does not have a centralized server. Queries made through the platform remain within the user's browser, and bookmarks are also stored locally. Therefore, users are solely responsible for backing up their bookmarks by using the export button on the Bookmark page.</p>
    `,
    about_why: "Why?",
    about_why_points: `
    <li>Unrestricted access to all knowledge is necessary for emerging new (semi-)digital lifeforms, such as AI and cyborgs</li>
    <li class="mt-3">The free flow of information promotes growth, while restriction leads to stagnation and starvation</li>
    <li class="mt-3">Withholding knowledge further perpetuates inequality amongst individuals and nations</li>
    <li class="mt-3">In the event of potential armageddon, private knowledge will not survive. However, freely replicating knowledge will serve as resurrection points for fallen civilizations</li>
    <li class="mt-3">Colonizing new worlds will require a reliable replication of knowledge, which is hardened by copyright</li>
    `,
    all_languages: 'All languages',
    bookmarks: 'bookmarks',
    contacts: "Contacts",
    donate: `<p>STC creators devote the most of their time to make knowledge available to every human. By supporting this project, you will be contributing to the democratization of knowledge and ensuring that everyone has access to the latest scholarly publications, regardless of their financial or institutional constraints. Even the smallest gift to charity can make a huge impact.</p>
    <p>We will appreciate any donations that will allow us to continue development of STC.</p>`,
    everywhere: 'Everywhere',
    found: 'found',
    help: `
    <h4 class="mt-4">Usage</h4>
    <p>Just type your request in plain words.</p>
    <h5>Examples</h5>
    <ul>
      <li class="font-monospace">Divine Comedy Dante</li>
      <li class="font-monospace">doi:10.1159/000477855</li>
      <li>Search by author:&nbsp;</li>
        <span class="font-monospace">authors:Jack authors:London</span>
      <li>Exact match:&nbsp;</li>
        <span class="font-monospace">"Fetal Hemoglobin"</span>
      <li>Filter formats (all except pdf):&nbsp;</li>
        <span class="font-monospace">+JavaScript extension:+epub</span>
      <li>All about JavaScript in Russian language:&nbsp;</li>
        <span class="font-monospace">+JavaScript language:+ru</span>
      <li>All about JavaScript excluding things in Russian language:&nbsp;</li>
        <span class="font-monospace">+JavaScript language:-ru</span>
    </ul>
    <p>Possible fields to use in queries may be found on <a href="/#/dbs">DBs page</a></p>
    `,
    is_ipfs_enabled: "Is local IPFS daemon enabled?",
    load_more: 'More',
    loading: 'loading',
    loading_document: 'loading document',
    network_error: "Network error, try to reload page",
    replicate_intro: `
    <h4>Replicate search metadata</h4>
    <p><b>Search metadata does not include books or scholar publications</b>. Follow the last section of this guide to learn about how to replicate them separately.</p>
    <p>STC is built on the <a href="https://izihawa.github.io/summa/">Summa</a> search engine which is used for replicating and serving queries. STC includes a search metadata, search engine, and web interface packed together in a single bundle available through IPFS.</p>
    <p>This bundle may be accessed directly through a web browser, or the dataset separately may be opened by the server version of Summa.</p>
    <p>Hence, here are two modes of replication: light and full.</p>
    `,
    replicate_replicate_data: `
    <h4>Replicate data</h4>
    <p>Books and scholarly articles need to be replicated separately. Here are two options for different levels of participation:</p>
    <h5 class="mt-2">Self-Standing Mode</h5>
    <p><i>Level: Easy / Medium</i></p>
    <div><p>Take recent published CID lists at <a href="https://t.me/nexus_search/">Telegram</a> and pin these CIDs.</p></div>
    <b>Linux/MacOS</b>
    <div>Open terminal and execute following command</div>
    <div><code>cat doi-cids.txt | shuf | xargs -P8 -L1 bash -c 'ipfs pin add $1'</code></div>
    <b>Windows</b>
    <div>Open PowerShell and switch Bash by typing <code>bash</code>. Ensure that <code>IPFS_PATH</code> environment variable is set correctly, otherwise set it to your IPFS directory: <code>export IPFS_PATH=/mnt/d/yourIPFSrepo/.ipfs/</code>. Then, begin the pinning:</div>
    <div><code>cat doi-cids.txt | shuf | xargs -P8 -L1 bash -c 'ipfs pin add $1'</code></div>
    <div>The average file size is 3,61MB. You may use it for calculating how many files you are capable to pin.</div>
    <h5 class="mt-3">Join Red Scriptorium IPFS Cluster</h5>
    <p><i>Level: Medium</i></p>
    <p>This approach requires you to install the <a href="https://ipfscluster.io/documentation/deployment/setup/">IPFS cluster software</a> and participate in cluster pinning. You will not have to download CIDs on your own, but will need to install a coordination agent that will receive and store files and CIDs automatically.</p>
    <p>Please join <a href="https://t.me/+wN8n75kr4nxlMmZi">Telegram chat</a> to receive the latest guidance.</p>
    `,
    search: 'Search',
    search_placeholder: 'by title, authors, content, doi...',
    unsupported_browser: "Unfortunately, you have unsupported browser. Try to update it or use another browser.",
    what_to_read: 'What To Read'
  },
  'pb': {
    all_languages: 'Todas as línguas',
    bookmarks: 'favoritas',
    donate: `<p>Os criadores do STC dedicam a maior parte de seu tempo para tornar o conhecimento disponível para todos os humanos. Ao apoiar este projeto, você estará contribuindo para a democratização do conhecimento e garantindo que todos tenham acesso às mais recentes publicações científicas, independentemente de suas restrições financeiras ou institucionais. Mesmo o menor presente para a caridade pode causar um grande impacto.</p>
    <p>Agradecemos qualquer doação que nos permita continuar o desenvolvimento do STC.</p>`,
    everywhere: 'Em toda parte',
    found: 'encontrado',
    load_more: 'Mais',
    loading: 'carregando',
    loading_document: 'carregando documento',
    search: 'Procurar',
    search_placeholder: 'título, autor, conteúdo, doi...',
    what_to_read: 'O que ler'
  },
  'ru': {
    about_alert: `
    <p>Стандартные шаблонные конструкции (STC) находятся в активной разработке.</p> 
    <p>Мы уже перенесли в STC:</p>
    <ul>
      <li>7 500 000 книг</li>
      <li>Более 1 000 000 свежих научных статей</li>
    </ul>
    <p>Тем не менее, еще многое предстоит сделать. Мы призываем <b>людей, способных сидировать данные и имеющих хороший интернет-канал</b> присоединиться к нам.</p>
    <p>Если вы заинтересованы, то свяжитесь с нами по контактам ниже.</p>
    <p>Если вы хотите поддержать разработку STC, вы можете <a href="/#/donate">сделать пожертвование в криптовалютах</a></p>
    `,
    all_languages: 'Все языки',
    bookmarks: 'закладок',
    contacts: "Как связаться с нами",
    donate: `<p>Создатели STC посвящают большую часть своего времени тому, чтобы сделать знания доступными для каждого человека. Поддерживая этот проект, вы внесете свой вклад в демократизацию знаний и обеспечите каждому доступ к последним научным публикациям, независимо от его финансовых или институциональных ограничений. Даже самый маленький взнос может оказать огромное влияние.</p>
    <p>Мы будем признательны за любые пожертвования, которые позволят нам продолжить развитие STC.</p>`,
    everywhere: 'Везде',
    found: 'найдено',
    load_more: 'Ещё',
    loading: 'загрузка',
    loading_document: 'загрузка документа',
    search: 'Поиск',
    search_placeholder: 'заголовок, автор, содержание, doi...',
    what_to_read: 'Что почитать'
  }
}

export function get_label(label: string) {
  for (const language in navigator.languages) {
    const language = navigator.language.slice(0, 2);
    if (language in translations) {
      if (label in translations[language]) {
        return translations[language][label];
      } else {
        break;
      }
    }
  }
  return translations['en'][label];
}