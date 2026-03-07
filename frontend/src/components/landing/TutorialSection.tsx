import { Box, Flex, Heading, Text, Stack } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { Search, Newspaper, Send } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import CTAButtons from './CTAButtons';

const MotionBox = motion.create(Box);
const MotionFlex = motion.create(Flex);
const MotionHeading = motion.create(Heading);
const MotionText = motion.create(Text);

interface TutorialSlide {
  icon: LucideIcon;
  title: string;
  steps: string[];
  mockupLabel: string;
  image: string;
}

const slides: TutorialSlide[] = [
  {
    icon: Search,
    title: 'Analyze a Topic',
    steps: [
      'Ask about any topic, product, or trend',
      'We crawl Reddit, YouTube, and Amazon for real-time data',
      'Get a structured intelligence report with sentiment analysis',
    ],
    mockupLabel: 'Analysis Report',
    image: '/images/analyze.png',
  },
  {
    icon: Newspaper,
    title: 'AI Daily Digest',
    steps: [
      'Open the AI Digest page from the sidebar',
      "View today's auto-generated intelligence briefing",
      'Share or export the digest as an image',
    ],
    mockupLabel: 'Daily Digest',
    image: '/images/digest.png',
  },
  {
    icon: Send,
    title: 'Connect Telegram',
    steps: [
      'Generate a bind code from Settings',
      'Send /bind YOUR_CODE to @SmIA_bot on Telegram',
      'Get analysis and digests delivered straight to Telegram',
    ],
    mockupLabel: 'Telegram Bot',
    image: '/images/telegram.png',
  },
];

export default function TutorialSection() {
  return (
    <Box
      as="section"
      aria-labelledby="tutorial-heading"
      bg="transparent"
      py={{ base: 16, md: 24 }}
      position="relative"
    >
      <Box maxW="6xl" mx="auto" px={{ base: 6, md: 12 }} position="relative">
        {/* Section heading */}
        <MotionHeading
          id="tutorial-heading"
          as="h2"
          size="3xl"
          color="white"
          textAlign="center"
          mb={{ base: 16, md: 24 }}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
        >
          How It{' '}
          <Text as="span" color="green.400">
            Works
          </Text>
        </MotionHeading>

        {/* Tutorial slides */}
        <Stack gap={{ base: 8, md: 10 }}>
        {slides.map((slide, index) => {
          const isReversed = index % 2 !== 0;
          const Icon = slide.icon;

          return (
            <MotionFlex
              key={slide.title}
              direction={{ base: 'column', md: isReversed ? 'row-reverse' : 'row' }}
              position="relative"
              alignItems="center"
              gap={{ base: 6, md: 12 }}
              overflow="hidden"
              bg="rgba(255, 255, 255, 0.02)"
              backdropFilter="blur(24px) saturate(180%) brightness(1.1)"
              borderWidth="1px"
              borderTopColor="rgba(255, 255, 255, 0.15)"
              borderLeftColor="rgba(255, 255, 255, 0.06)"
              borderRightColor="rgba(255, 255, 255, 0.06)"
              borderBottomColor="rgba(255, 255, 255, 0.03)"
              borderRadius="2xl"
              boxShadow="0 8px 32px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.12), inset 0 -1px 0 rgba(255, 255, 255, 0.03)"
              p={{ base: 6, md: 10 }}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true, margin: '-100px' }}
              transition={{ duration: 0.5 }}
            >
              {/* Mockup side */}
              <MotionBox
                w="100%"
                maxW={{ base: '100%', md: '50%' }}
                initial={{ opacity: 0, x: isReversed ? 40 : -40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: 0.1 }}
              >
                <Box
                  position="relative"
                  borderRadius="xl"
                  overflow="hidden"
                  bg="rgba(74, 222, 128, 0.05)"
                  border="1px solid rgba(74, 222, 128, 0.1)"
                >
                  <img
                    src={slide.image}
                    alt={slide.mockupLabel}
                    loading="lazy"
                    style={{ width: '100%', height: 'auto', display: 'block' }}
                  />
                </Box>
              </MotionBox>

              {/* Text side */}
              <MotionBox
                w="100%"
                maxW={{ base: '100%', md: '50%' }}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: 0.2 }}
              >
                <Stack
                  gap={5}
                  borderLeft="3px solid"
                  borderLeftColor="green.400"
                  pl={6}
                >
                  {/* Number badge + title */}
                  <Flex alignItems="center" gap={3}>
                    <Flex
                      w="36px"
                      h="36px"
                      borderRadius="full"
                      bg="green.400"
                      color="black"
                      alignItems="center"
                      justifyContent="center"
                      fontWeight="bold"
                      fontSize="sm"
                      flexShrink={0}
                    >
                      {index + 1}
                    </Flex>
                    <Flex alignItems="center" gap={2}>
                      <Icon size={20} color="#4ade80" />
                      <Heading size="xl" color="white">
                        {slide.title}
                      </Heading>
                    </Flex>
                  </Flex>

                  {/* Steps */}
                  <Stack as="ol" gap={3} pl={0} listStyleType="none">
                    {slide.steps.map((step, stepIndex) => (
                      <MotionText
                        as="li"
                        key={stepIndex}
                        color="gray.300"
                        fontSize="md"
                        lineHeight="1.7"
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.4, delay: 0.3 + stepIndex * 0.1 }}
                      >
                        <Text as="span" color="green.400" fontWeight="semibold" mr={2}>
                          {stepIndex + 1}.
                        </Text>
                        {step}
                      </MotionText>
                    ))}
                  </Stack>
                </Stack>
              </MotionBox>
            </MotionFlex>
          );
        })}
        </Stack>

        {/* Closing CTA */}
        <MotionBox
          textAlign="center"
          py={{ base: 16, md: 24 }}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6 }}
        >
          <Heading size="xl" color="white" mb={8}>
            Ready to get started?
          </Heading>
          <Flex justifyContent="center">
            <CTAButtons />
          </Flex>
        </MotionBox>
      </Box>
    </Box>
  );
}
