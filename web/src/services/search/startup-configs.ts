import { summa, seeds } from "summa-wasm";

export async function get_startup_configs() {
  const is_development =
    process.env.NODE_ENV === "development" || window.location.port === "5173";
  const ipfs_url = is_development ? "http://localhost:8080" : undefined;
  return [
    {
      index_name: "nexus_free",
      seed: is_development
        ? new seeds.IpfsDatabaseSeed(
            "/ipfs/bafyb4ics4mkbagdxjjlm5k2styz4wscdbxjpwwojkgrowcdydvs4lnaj3e/",
            new summa.proto.CacheConfig({cache_size: 128 * 1024 * 1024}),
            ipfs_url
          )
        : new seeds.LocalDatabaseSeed(
            "/data/nexus_free",
            new summa.proto.CacheConfig({cache_size: 128 * 1024 * 1024})
          ),
      is_enabled: true,
      query_parser_config: {
        field_aliases: {
          author: "authors.name",
          authors: "authors.name",
          cid: "links.cid",
          isbns: "id.isbns",
          issns: "metadata.issns",
          lang: "language",
          pub: "metadata.publisher",
          ser: "metadata.series",
        },
        field_boosts: {
          title: 1.3
        },
        term_field_mapper_configs: {
          doi_isbn: {fields: ['id.isbns']},
          isbn: {fields: ['id.isbns']},
        },
        term_limit: 10,
        default_fields: ["abstract", "title"],
        exact_matches_promoter: {
          'slop': 0,
          'boost': 1.5,
          'fields': ['title']
        },
        removed_fields: ["doi", "rd", "ev"],
      },
      is_exact_matches_promoted: true,
      is_fieldnorms_scoring_enabled: false,
      is_temporal_scoring_enabled: false,
    },
    {
      index_name: "nexus_media",
      seed: is_development
        ? new seeds.IpfsDatabaseSeed(
            "/ipfs/bafyb4if3exj3o2u3sm2s4xvbeu7fkpwm62g7euuzwlfffvq6nbbwueeloq/",
            new summa.proto.CacheConfig({cache_size: 128 * 1024 * 1024}),
            ipfs_url
          )
        : new seeds.LocalDatabaseSeed(
            "/data/nexus_media",
            new summa.proto.CacheConfig({cache_size: 128 * 1024 * 1024})
          ),
      query_parser_config: {
        field_aliases: {
          lang: "language",
        },
        field_boosts: {
          title: 1.3
        },
        term_field_mapper_configs: {},
        term_limit: 10,
        default_fields: ["title"],
        exact_matches_promoter: {
          'slop': 0,
          'boost': 1.5,
          'fields': ['title']
        },
        removed_fields: [],
      },
      is_enabled: false,
      is_fieldnorms_scoring_enabled: false,
      is_temporal_scoring_enabled: false,
    },
    {
      index_name: "nexus_science",
      seed: is_development
        ? new seeds.IpfsDatabaseSeed(
            "/ipfs/bafyb4ibo4h574kj6khe2twsfmo2azxwo77ysc4pxjmh5deup6rntxtlcra/",
            new summa.proto.CacheConfig({cache_size: 512 * 1024 * 1024}),
            ipfs_url
          )
        : new seeds.LocalDatabaseSeed(
            "/data/nexus_science",
            new summa.proto.CacheConfig({cache_size: 512 * 1024 * 1024})
          ),
      query_parser_config: {
        field_aliases: {
          author: "authors.family",
          authors: "authors.family",
          cid: "links.cid",
          isbns: "id.isbns",
          issns: "metadata.issns",
          lang: "language",
          ev: "metadata.event.name",
          pub: "metadata.publisher",
          ser: "metadata.series",
        },
        field_boosts: {
          title: 1.3
        },
        term_field_mapper_configs: {
          doi: {fields: ['doi']},
          doi_isbn: {fields: ['metadata.isbns']},
          isbn: {fields: ['metadata.isbns']},
        },
        term_limit: 10,
        default_fields: ["abstract", "title"],
        exact_matches_promoter: {
          'slop': 0,
          'boost': 1.5,
          'fields': ['title']
        },
        removed_fields: ["id"],
      },
      is_enabled: true,
      is_fieldnorms_scoring_enabled: false,
      is_temporal_scoring_enabled: false,
    },
  ];
}
