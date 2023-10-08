<template lang="pug">
.container
  h2 Welcome, seeker!
  p 欢迎，探索者！- आपका स्वागत है, साधक! - ¡Bienvenido buscador! - Bem-vindo, buscador! - مرحبًا بك أيها الباحث! - Добро пожаловать, искатель!
  ul
    li
      a(href="#/nexus_science/cid:bafykbzaceayxkpz5tk6nuqjzoidix4y4lakfwvzkmfisycduijcwfew7waa5e") English through pictures
    li
      a(href="#/?q=english+for+beginners&p=1&d=nexus_science") Further sources for learning English
  h4 {{ get_label('about') }}
  span(v-html="get_label('about_intro')")
  hr
  img.img-fluid(id="origin", src="@/assets/origin.jpg")
</template>
<script lang="ts">
import { defineComponent } from 'vue'

import { get_label } from '../translations'
export default defineComponent({
  name: 'IntroView',
  created () {
    document.title = 'Welcome - Help - STC'
    const description = document.querySelector('head meta[name="description"]')
    if (description != null) {
      description.setAttribute('content', get_label('about_intro'))
    }
  },
  methods: { get_label }
})
</script>

<style lang="scss" scoped>
#origin {
  border-width: 20px;
  border-radius: 20px;
  border-color: #111111;
  border-style: solid;
}
</style>
